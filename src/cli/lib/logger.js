export function createLogger(options = {}) {
  const verbose = Boolean(options.verbose);

  return {
    info(message) {
      console.log(message);
    },
    warn(message) {
      console.warn(`WARN: ${message}`);
    },
    fail(message) {
      console.error(`FAIL: ${message}`);
    },
    pass(message) {
      console.log(`PASS: ${message}`);
    },
    verbose(message) {
      if (verbose) {
        console.log(message);
      }
    }
  };
}
