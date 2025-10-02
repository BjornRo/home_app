import type { LayoutLoad, LayoutLoadEvent } from "./$types";
import { error, redirect } from "@sveltejs/kit";
import { api_fetch_event } from "$lib/utils/func";
import { ACCESS_COOKIE_STATE, TOKEN_PATH, type UserData } from "$lib/utils/const";
import { credentials } from "$lib/utils/stores";

export const csr = true;
export const ssr = false;

const fetch_access_token = async (event: LayoutLoadEvent): Promise<boolean> => {
    const token_resp = await api_fetch_event(event, TOKEN_PATH);
    if (token_resp.ok) {
        const data_resp = await api_fetch_event(event, "user/self/data");
        if (!data_resp.ok) {
            // Should not happen
            throw error(500, "Something bad happened? :(");
        }
        event.data.credentials = {
            data: (await data_resp.json()) as UserData,
            token_expiry: parseInt(await token_resp.text(), 10),
        };
        event.data.access_state = ACCESS_COOKIE_STATE.LOGGED_IN;
        credentials.set(event.data.credentials);
        return true;
    }
    // User does not have refresh-token or invalid refresh-token
    if (event.data.access_state === ACCESS_COOKIE_STATE.LOGGED_IN) {
        redirect(303, "/login");
    }
    event.data.access_state = ACCESS_COOKIE_STATE.VISITOR;
    return false;
};

export const load: LayoutLoad = async (event) => {
    switch (event.data.access_state) {
        case ACCESS_COOKIE_STATE.LOGGED_IN:
            if (event.data.credentials) {
                credentials.set(event.data.credentials);
                break;
            }
        case ACCESS_COOKIE_STATE.NEW:
            if (await fetch_access_token(event)) {
                window.location.reload();
            }
            await api_fetch_event(event, "auth/null_access");
        case ACCESS_COOKIE_STATE.VISITOR:
        default:
        // if (document.cookie.indexOf(ACCESS_TOKEN) === -1) {
        //     document.cookie = `${ACCESS_TOKEN}=null; SameSite=lax; Domain=.${HOSTNAME}; Path=/`;
        // }
    }
    return { navbar_items: event.data.navbar_items, user_data: event.data.credentials?.data };
};
