import { sveltekit } from "@sveltejs/kit/vite";
import { HOSTNAME } from "./src/lib/utils/const";

/** @type {import('vite').UserConfig} */
const config = {
    // server: { host: HOSTNAME },
    plugins: [sveltekit()],
    test: {
        include: ["src/**/*.{test,spec}.{js,ts}"],
    },
};

export default config;
