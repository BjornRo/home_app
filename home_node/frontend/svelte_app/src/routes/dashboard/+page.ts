// import * as store from '$app/stores';
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ data, fetch }) => {
    return { logged_in: true };
};
