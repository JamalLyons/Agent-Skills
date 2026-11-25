# Browser review

Read this only when the request asks for browser work, a recording, responsive or theme review, or an inline mockup. Use the current host's browser tooling; the T3 Code tool names below are one concrete adapter.

## T3 Code adapter

Use these tools when the user asks for browser work, asks to record UI changes, or identifies a page or tab. Do not use them for routine code edits just to verify or show your own work.

- Start with `preview_status`. If no suitable tab is available, use `preview_open` for the requested page. Respect tab ownership; operate only on a tab owned by this agent or an unclaimed tab.
- Use `preview_snapshot` to inspect the requested page. Set `includeImage: true` when visual inspection is requested. Prefer its accessibility-tree `aria-ref` locators with `preview_act` over coordinates. Take a fresh snapshot after navigation because refs expire.
- For requested responsive review, use `preview_resize` to check a phone-sized viewport and the relevant desktop size. Use `preview_set_appearance` when the requested review includes light or dark mode. Restore the user's prior viewport or appearance when practical.
- Use `preview_recording_start` and `preview_recording_stop` only when the user asks for a recording. Close a tab opened for the task with `t3_preview_close` before replying, unless the user asked to keep it open.
- For a self-contained HTML mockup the user asks to see inline, call `html_preview` first, then `html_render` using its `contentHeight`. Keep the HTML self-contained; do not start a server for these tools. Use the render constraints from the tool description, including theme variables and frame sizing. These tools display a mockup; they do not replace implementing the requested project UI.

When these T3 Code tools are unavailable, use the current host's supported browser workflow when the request calls for one. Keep the design and implementation usable without any T3-specific tool.
