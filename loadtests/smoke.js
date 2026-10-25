// Smoke: one user for 30 seconds. Does the script work and the API answer?
import { shop } from "./lib.js";

export const options = {
  vus: 1,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate==0"],
    http_req_duration: ["p(95)<250"],
  },
};

export default function () {
  shop();
}
