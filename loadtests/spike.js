// Spike: normal traffic, then a sudden burst above capacity, then normal
// again. The question is not whether it survives the burst, but whether it
// recovers once the burst is over.
import { shop } from "./lib.js";

export const options = {
  scenarios: {
    spike: {
      executor: "ramping-arrival-rate",
      startRate: 20,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 2000,
      stages: [
        { target: 20, duration: "1m" }, // normal
        { target: 450, duration: "10s" }, // burst, about 1.5x capacity
        { target: 450, duration: "1m" },
        { target: 20, duration: "10s" }, // back to normal
        { target: 20, duration: "2m" }, // does it recover?
      ],
    },
  },
  thresholds: {
    // No abort: the point is to watch the whole curve, including recovery.
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  shop();
}
