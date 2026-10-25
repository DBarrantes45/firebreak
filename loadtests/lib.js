import http from "k6/http";
import { check } from "k6";

export const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// Marks every request as load test traffic, so the SLOs leave it out.
const HEADERS = { "Content-Type": "application/json", "X-Load-Test": "k6" };

// One "user action": four product reads for every order, like real shopping.
export function shop() {
  if (Math.random() < 0.8) {
    const res = http.get(`${BASE_URL}/products`, { headers: HEADERS, tags: { route: "/products" } });
    check(res, { "products 200": (r) => r.status === 200 });
  } else {
    const body = JSON.stringify({ product_id: 1, quantity: 1 });
    const res = http.post(`${BASE_URL}/orders`, body, { headers: HEADERS, tags: { route: "/orders" } });
    check(res, { "order 201": (r) => r.status === 201 });
  }
}
