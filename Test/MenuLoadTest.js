// PWA-08 (PrdOpsAndPwaClose.md section 13, S5-Q3): 50 guests behind one cafe NAT IP keep the menu open.
// Each virtual user fetches the catalog and the CMS every 5 seconds for 60 seconds through the production
// Nginx config. Gate: zero 429 and zero failed GETs. The cache hit ratio is read from the Nginx access log.
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const base = __ENV.NGINX_URL || "http://127.0.0.1:18090";
const store = __ENV.STORE_SLUG || "e2e-kasir";
const tooMany = new Counter("menu_429");

export const options = {
  vus: 50,
  duration: "60s",
  thresholds: {
    menu_429: ["count==0"],
    http_req_failed: ["rate==0"],
  },
};

export default function () {
  for (const path of ["catalog", "cms"]) {
    const res = http.get(`${base}/api/v1/public/stores/${store}/${path}`);
    if (res.status === 429) tooMany.add(1);
    check(res, { [`${path} 200`]: (r) => r.status === 200 });
  }
  sleep(5);
}
