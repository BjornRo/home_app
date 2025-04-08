import { app_user_cache } from "$lib/server/stores";
import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "../$types";
import { unsafe_jwt_to_payload_sign } from "$lib/server/utils";

export const load: LayoutServerLoad = async (event) => {
    const token_str = event.locals.credentials?.token.raw_token;
    if (token_str) {
        app_user_cache.del(unsafe_jwt_to_payload_sign(token_str));
    }
    redirect(303, "/");
};
