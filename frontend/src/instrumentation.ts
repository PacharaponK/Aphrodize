import type { Instrumentation } from "next";

export const onRequestError: Instrumentation.onRequestError = (_error, request, context) => {
  const id = request.headers["x-request-id"];
  console.error(JSON.stringify({ timestamp: new Date().toISOString(), service: "frontend",
    event: "request_error", route: context.routePath, method: request.method,
    request_id: typeof id === "string" && /^[0-9a-f]{32}$/i.test(id) ? id : "" }));
};
