"""Read a remote .laz header without downloading the file.

`HttpRangeFile` is a seekable, read-only file object over HTTP range requests, so laspy
can open a LAZ on the objectstore and read its header and VLRs while transferring only
the bytes it touches. It counts what it transfers, which is how the header-read cost was
measured (research/laz_header_read.md).
"""

import io

import requests

BLOCK = 64 * 1024


class HttpRangeFile(io.RawIOBase):
    """Seekable read-only view of a URL, fetched in BLOCK-sized range requests."""

    def __init__(self, url: str, session: requests.Session | None = None, timeout: float = 30):
        self.url = url
        self.session = session or requests.Session()
        self.timeout = timeout
        head = self.session.head(url, timeout=timeout, allow_redirects=True)
        head.raise_for_status()
        # No Accept-Ranges check: the objectstore honours ranges (206) without
        # advertising them, measured 2026-10-07. _block() refuses anything but a 206.
        self.size = int(head.headers["Content-Length"])
        # Which delivery of the file was read: a re-delivered file has a new ETag.
        self.etag = head.headers.get("ETag", "").strip('"')
        self.pos = 0
        self.bytes_fetched = 0
        self.requests = 0
        self._blocks: dict[int, bytes] = {}

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        else:
            raise ValueError(f"bad whence {whence}")
        return self.pos

    def _block(self, i: int) -> bytes:
        if i not in self._blocks:
            start = i * BLOCK
            end = min(start + BLOCK, self.size) - 1
            r = self.session.get(self.url, headers={"Range": f"bytes={start}-{end}"},
                                 timeout=self.timeout)
            if r.status_code != 206:
                raise OSError(f"range request returned {r.status_code}, not 206: {self.url}")
            self._blocks[i] = r.content
            self.bytes_fetched += len(r.content)
            self.requests += 1
        return self._blocks[i]

    def read(self, n: int = -1) -> bytes:
        if self.pos >= self.size:
            return b""
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        out = bytearray()
        while n > 0:
            i, off = divmod(self.pos, BLOCK)
            chunk = self._block(i)[off:off + n]
            if not chunk:
                break
            out += chunk
            self.pos += len(chunk)
            n -= len(chunk)
        return bytes(out)

    def readinto(self, b) -> int:
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)
