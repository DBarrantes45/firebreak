// Steady "user" traffic for game days. Open model: users keep arriving at
// the same rate even when the API slows down. A closed loop (send, wait,
// send again) would slow down with the API and hide part of the problem.
import { shop } from "./lib.js";

export const options = {
  scenarios: {
    users: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "40m",
      preAllocatedVUs: 20,
      maxVUs: 200,
    },
  },
};

export default function () {
  shop();
}
