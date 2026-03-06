import concurrent.futures

from ...constants import Constant


thread_pools = []

for _ in range(Constant.MAX_NPU_SIZE):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    thread_pools.append(pool)


