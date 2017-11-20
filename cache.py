import os, time
import msgpack 
from hashlib import sha1
import functools
import errno

def mkdirs_safe(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

# Defaults to 15 days (1,296,000 sec)
def cache_disk(cache_root="/tmp/cachepy", stale_seconds = 1296000):
    def doCache(f):
        #@functools.wraps(f)
        def inner_function(*args, **kwargs):
            # calculate a cache key based on the decorated method signature
            key = sha1(msgpack.packb((f.__module__, f.__name__, args, kwargs))).hexdigest()
            
            # Make sure the cach path exists
            cache_path = os.path.join(cache_root, f.__name__)
            mkdirs_safe(cache_path)
            fn = os.path.join(cache_path, key)

            # Check if the cached object exists and is fresh
            if os.path.exists(fn):
                modified = os.path.getmtime(fn)
                age_seconds = time.time() - modified
                if age_seconds < stale_seconds:
                    return msgpack.unpackb(open(fn, "rb").read())

            # Otherwise call the decorated function
            result = f(*args, **kwargs)

            # Save the cached object for next time
            with open(fn, 'wb+') as cachefile:
                cachefile.write(msgpack.packb(result))

            return result
        return inner_function
    return doCache
    