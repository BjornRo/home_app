import type { LayoutServerLoad } from "./$types";
import { ACCESS_COOKIE_STATE, type KeyValueItem } from "$lib/utils/const";
import type { AppUser } from "$lib/server/const";
import { user_token_to_data_token } from "$lib/server/utils";

const load_navbar_items = async (app_user: AppUser): Promise<KeyValueItem[]> => {
    const items = [];
    if (app_user.is_root()) {
        items.push({ key: "Admin Panel", value: "/admin" });
    }
    return items;
};

export const load: LayoutServerLoad = async (event) => {
    let navbar_items: KeyValueItem[] = [];
    let new_credentials = null;

    const access_state = event.locals.access_cookie_state;
    if (access_state === ACCESS_COOKIE_STATE.LOGGED_IN) {
        const creds = event.locals.credentials;
        if (creds) {
            navbar_items = await load_navbar_items(creds.user);
            new_credentials = user_token_to_data_token(creds);
        }
    }

    return {
        navbar_items: navbar_items,
        credentials: new_credentials,
        access_state: access_state,
    };
};
