// Soak: normal load for a long time. With chaos off, memory should stay flat;
// if it climbs on its own, there is a leak nobody programmed.
import { shop } from "./lib.js";

export const options = {
  scenarios: {
    soak: {
      executor: "constant-arrival-rate",
      rate: 30,
      timeUnit: "1s",
      duration: __ENV.SOAK_DURATION || "1h",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.001"],
    "http_req_duration{expected_response:true}": ["p(99)<250"],
  },
};

export default function () {
  shop();
}
