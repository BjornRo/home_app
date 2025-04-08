// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types
// npm run dev -- --open

import type { UserToken } from "$lib/server/const";
import type { ACCESS_COOKIE_STATE } from "$lib/utils/const";

declare global {
    namespace App {
        // interface Error {}
        interface Locals {
            credentials: UserToken | undefined;
            access_cookie_state: ACCESS_COOKIE_STATE;
        }
        // interface PageData {}
        // interface Platform {}
    }
}

export {};
