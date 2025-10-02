// import * as store from '$app/stores';
import { get } from "svelte/store";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ locals, fetch }) => {
    // console.log(get(token)?.sub);
    return { val: 123 };
};
