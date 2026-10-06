// Wait after each response so slow requests cannot accumulate in-flight polls.
export function startResultPolling(fetchResult, onResult, onError,
  timers = { schedule: setTimeout, cancel: clearTimeout }) {
  const controller = new AbortController();
  let stopped = false;
  let timer;
  const stop = () => {
    stopped = true;
    timers.cancel(timer);
    controller.abort();
  };
  const poll = async () => {
    try {
      const data = await fetchResult(controller.signal);
      if (stopped) return;
      if (onResult(data) === false) {
        stop();
        return;
      }
      timer = timers.schedule(poll, 2000);
    } catch (error) {
      if (stopped) return;
      stop();
      onError(error);
    }
  };
  timer = timers.schedule(poll, 2000);
  return stop;
}
