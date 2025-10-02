import type { PageServerLoad } from "./$types";
import { user_token_to_data_token } from "$lib/server/utils";

export const load: PageServerLoad = async (event) => {
    let creds = event.locals.credentials;
    let new_creds = undefined;
    if (creds) {
        new_creds = user_token_to_data_token(creds);
    }
    return { credentials: new_creds, access_cookie_state: event.locals.access_cookie_state };
};
