import { ACCESS_COOKIE_STATE, API_HOST, TOKEN_PATH } from "$lib/utils/const";
import { redirect } from "@sveltejs/kit";
import type { Handle, HandleFetch, RequestEvent } from "@sveltejs/kit";
import { api_fetch_srv, jsobj_to_appuser, naive_decode_jwt_srv } from "$lib/server/utils";
import { ACCESS_TOKEN, is_expired, REFRESH_TOKEN } from "$lib/utils/token";
import { app_user_cache } from "$lib/server/stores";
import { AppUser, IP_HEADER, LOCAL_API_HOST } from "$lib/server/const";
import { jwt_time_diff_sec } from "$lib/server/token";
/*
https://kit.svelte.dev/docs/hooks
*/

const parse_and_set_credentials = async (event: RequestEvent): Promise<ACCESS_COOKIE_STATE> => {
    const access_token = event.cookies.get(ACCESS_TOKEN);
    if (!access_token) {
        return ACCESS_COOKIE_STATE.NEW;
    }
    const _PACKED_CLAIMS = access_token === "null" ? null : naive_decode_jwt_srv(access_token);
    // Checking the validity of the jwt occurs when fetching user_data from the API.
    if (_PACKED_CLAIMS === null) {
        return ACCESS_COOKIE_STATE.VISITOR;
    }

    const { claims, cache_key } = _PACKED_CLAIMS;
    if (is_expired(claims.exp, 10)) {
        // As we do not know the state of the refresh token, we need to handle this case in on client side.
        // Client side will first check the expiry date of the "access token" which is expired,
        // and also see that the state is LOGGED_IN. Request a new token from token_path and then refresh/redirect
        return ACCESS_COOKIE_STATE.LOGGED_IN;
    }
    let app_user: AppUser | undefined = app_user_cache.get(cache_key);
    if (!app_user) {
        const res = await api_fetch_srv(event, claims, `user/${claims.sub}/app`);
        if (res.ok) {
            app_user = (await res.json()) as AppUser; // AppUser-class to get attributes only
            app_user_cache.set(cache_key, app_user, jwt_time_diff_sec(claims.exp));
        }
    }
    if (app_user) {
        event.locals.credentials = {
            user: jsobj_to_appuser(app_user),
            token: claims,
        };
        return ACCESS_COOKIE_STATE.LOGGED_IN;
    }
    event.cookies.set(ACCESS_TOKEN, "null", { path: "/", httpOnly: true, secure: false });
    event.cookies.set(REFRESH_TOKEN, "null", { path: "/auth", httpOnly: true, secure: false });
    return ACCESS_COOKIE_STATE.VISITOR;
};

export const handle: Handle = async ({ event, resolve }) => {
    event.locals.access_cookie_state = await parse_and_set_credentials(event);
    const PATH = event.url.pathname;
    if (PATH.startsWith("/admin")) {
        const is_root = event.locals.credentials?.user.is_root();
        if (!is_root) {
            if (event.locals.access_cookie_state !== ACCESS_COOKIE_STATE.LOGGED_IN || is_root === false) {
                redirect(303, "/");
            }
            // When redirect loads, it checks for a new token, then redirects to the given path.
            // If a login is not valid, then cookie state will be visitor.
            redirect(303, `/redirect?to=${PATH}`);
        }
    }

    const resp = await resolve(event);
    if (resp.status === 404) {
        redirect(303, "/404_narnia");
    }
    return resp;
};

export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
    if (request.url.startsWith(API_HOST)) {
        request.headers.append(IP_HEADER, event.getClientAddress());
        request = new Request(request.url.replace(API_HOST, LOCAL_API_HOST), request);
    }
    const resp = await fetch(request);
    return resp;
};
