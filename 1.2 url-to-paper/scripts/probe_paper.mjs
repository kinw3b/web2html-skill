import { call, setFileId } from "./mcp-client.mjs";
const fileId = "01M319JNTDWFMAR6J3CCRQ52M8";
setFileId(fileId);
const opened = await call("open_file", { fileId, pageId: undefined });
console.log("open_file ok");
const r = await call("get_jsx", { fileId, format: "inline-styles", nodeId: "2US-0" });
console.log("get_jsx content lens:", (r.content||[]).map(c=>(c.text||"").length));
console.log("body head:", (r.content?.[0]?.text||"").slice(0,60).replace(/\n/g," "));
console.log("tail head:", (r.content?.[1]?.text||"").slice(0,60).replace(/\n/g," "));
