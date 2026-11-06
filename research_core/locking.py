# SPDX-License-Identifier: Apache-2.0
"""One local research operation across threads and processes, no daemon."""
import fcntl,threading,os
from pathlib import Path
from esae.scanner import no_symlink

class OperationLock:
    def __init__(self,path):self.path=Path(path);self.thread=threading.Lock();self.handle=None
    def acquire(self,blocking=False):
        if not self.thread.acquire(blocking=blocking):return False
        try:
            no_symlink(self.path);self.handle=self.path.open('a+b');os.chmod(self.path,0o600)
            fcntl.flock(self.handle,fcntl.LOCK_EX|(0 if blocking else fcntl.LOCK_NB));return True
        except BlockingIOError:
            self.handle.close();self.handle=None;self.thread.release();return False
        except BaseException:
            if self.handle:self.handle.close();self.handle=None
            self.thread.release();raise
    def release(self):
        if self.handle:fcntl.flock(self.handle,fcntl.LOCK_UN);self.handle.close();self.handle=None
        self.thread.release()
    def locked(self):
        if self.thread.locked():return True
        if not self.acquire(False):return True
        self.release();return False
