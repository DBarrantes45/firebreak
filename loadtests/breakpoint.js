// Breakpoint: raise the request rate step by step until the SLO breaks,
// then stop. The rate reached at that moment is the capacity.
import { shop } from "./lib.js";

export const options = {
  scenarios: {
    breakpoint: {
      // Open model: the rate climbs no matter how slow the API gets.
      executor: "ramping-arrival-rate",
      startRate: 50,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 2000,
      // +50 requests per second every 30 seconds, up to 1500.
      stages: Array.from({ length: 29 }, (_, i) => ({ target: 100 + i * 50, duration: "30s" })),
    },
  },
  thresholds: {
    // Stop as soon as either SLO is clearly broken. delayAbortEval avoids
    // aborting on the first noisy seconds.
    http_req_failed: [{ threshold: "rate<0.001", abortOnFail: true, delayAbortEval: "10s" }],
    "http_req_duration{expected_response:true}": [
      { threshold: "p(99)<250", abortOnFail: true, delayAbortEval: "10s" },
    ],
  },
};

export default function () {
  shop();
}
