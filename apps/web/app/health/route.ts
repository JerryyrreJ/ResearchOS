export async function GET() {
  return Response.json({
    status: "ok",
    service: "researchos-web",
    mode: "fixture",
    contract: "0.1.0-frozen",
  }, { headers: { "cache-control": "no-store" } });
}
