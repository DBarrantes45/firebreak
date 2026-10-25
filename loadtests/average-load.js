// Average load: a steady 20 requests per second for 3 minutes, judged
// against the SLOs (99.9% success, 99% of successful requests under 250 ms).
import { shop } from "./lib.js";

export const options = {
  scenarios: {
    average: {
      // Open model: k6 keeps sending 20 rps even if the API slows down,
      // like real users who don't wait for each other.
      executor: "constant-arrival-rate",
      rate: 20,
      timeUnit: "1s",
      duration: "3m",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.001"],
    "http_req_duration{expected_response:true}": ["p(99)<250"],
    dropped_iterations: ["count==0"],
  },
};

export default function () {
  shop();
}
