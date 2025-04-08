import { error, redirect } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { app_user_cache } from "$lib/server/stores";
import {
    api_fetch_srv,
    jsobj_to_appuser,
    unsafe_jwt_to_payload_sign,
    parse_cookie,
    unsafe_decode_jwt_srv,
} from "$lib/server/utils";
import type { Token } from "$lib/server/token";
import type { AppUser } from "$lib/server/const";
import { ACCESS_TOKEN, REFRESH_TOKEN } from "$lib/utils/token";
import { ACCESS_COOKIE_STATE, HOSTNAME } from "$lib/utils/const";
import { api_path } from "$lib/utils/func";

export const load: PageServerLoad = async ({ locals }) => {
    return {};
};

export const actions = {
    // default: async (event) => {
    // 	console.log(event);
    // },
    logout: async (event) => {
        const token = event.locals.credentials?.token;
        if (token) {
            const resp = await api_fetch_srv(event, token, "auth/logout");
            if (resp.ok) {
                app_user_cache.del(unsafe_jwt_to_payload_sign(token.raw_token));
            }
        }
        event.cookies.delete(ACCESS_TOKEN, {
            path: "/",
            domain: `.${HOSTNAME}`,
            secure: false,
            httpOnly: true,
        });
        event.cookies.delete(REFRESH_TOKEN, {
            path: "/auth/",
            domain: `.${HOSTNAME}`,
            secure: false,
            httpOnly: true,
        });
        event.locals.credentials = undefined;
        event.locals.access_cookie_state = ACCESS_COOKIE_STATE.VISITOR;
        redirect(303, "/");
    },
    login: async (event) => {
        const { cookies, request, fetch, getClientAddress } = event;
        const data = await request.formData();
        const name = data.get("form_user")?.toString();
        const pwd = data.get("form_pwd")?.toString();
        if (name === undefined || name.length <= 0 || pwd === undefined || pwd.length <= 0) {
            throw error(400, "invalid name or empty password");
        }

        const resp = await fetch(api_path("auth/login"), {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Real-IP": getClientAddress() },
            body: JSON.stringify({
                name: name,
                pwd: pwd,
            }),
        });
        if (!resp.ok) {
            throw error(resp.status, JSON.stringify(await resp.json()));
        }
        const { claims, cache_key } = unsafe_decode_jwt_srv(((await resp.json()) as Token).access_token);
        const appuser_data = await api_fetch_srv(event, claims, `user/${claims.sub}/app`);
        if (!appuser_data.ok) {
            throw error(appuser_data.status, "Should not happen, unless? :(");
        }
        const appuser = (await appuser_data.json()) as AppUser;
        app_user_cache.set(cache_key, appuser, claims.exp);
        event.locals.credentials = { user: jsobj_to_appuser(appuser), token: claims };
        event.locals.access_cookie_state = ACCESS_COOKIE_STATE.LOGGED_IN;

        const remember = data.get("form_remember") === "1";
        resp.headers.getSetCookie().forEach((cookie) => {
            const { name, value, opts } = parse_cookie(cookie);
            opts.secure = false;
            if (!remember) {
                opts.expires = undefined;
            }

            cookies.set(name, value, opts);
        });
        redirect(303, event.url.pathname);
    },
};
