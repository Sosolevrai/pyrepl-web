const server = Bun.serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);
    
    if (url.pathname === "/") {
      return new Response(Bun.file("examples/index.html"));
    }
    
    if (url.pathname === "/embed.js") {
      const build = await Bun.build({
        entrypoints: ["src/embed.ts"],
      });
      return new Response(build.outputs[0], {
        headers: { "Content-Type": "application/javascript" },
      });
    }

    if (url.pathname === "/python/console.py") {
        return new Response(Bun.file("src/python/console.py"), {
            headers: { "Content-Type": "text/plain" },
        });
        }
    
    return new Response("Not found", { status: 404 });
  },
});

console.log(`http://localhost:${server.port}`);