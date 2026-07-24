import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "星星家庭 ABA 智能助手",
        short_name: "星星家庭",
        description: "面向自闭症儿童家庭的训练与成长支持工具",
        theme_color: "#6750a4",
        background_color: "#f7f5fb",
        display: "standalone",
        start_url: "/",
        icons: []
      }
    })
  ],
  server: {
    proxy: { "/api": "http://localhost:8000" }
  }
});

