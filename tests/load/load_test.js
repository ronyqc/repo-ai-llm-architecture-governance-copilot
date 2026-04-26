import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "1m",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<10000"],
  },
};

const BASE_URL =
  __ENV.E2E_API_BASE_URL ||
  "https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io";

const TOKEN = __ENV.TEST_JWT_TOKEN;

export default function () {
  const payload = JSON.stringify({
    query:
      "Según el documento Demo RAG Entregable 3.3, ¿qué building blocks se recomiendan para la apertura digital de tarjeta de crédito?",
    stream: false,
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
    },
    timeout: "60s",
  };

  const res = http.post(`${BASE_URL}/api/v1/query`, payload, params);
  console.log(`status=${res.status}, body=${res.body}`);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "has answer": (r) => {
      try {
        return JSON.parse(r.body).answer.length > 0;
      } catch {
        return false;
      }
    },
    "has sources": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.sources);
      } catch {
        return false;
      }
    },
  });

  sleep(1);
}