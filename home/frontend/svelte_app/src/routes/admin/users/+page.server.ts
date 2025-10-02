import type { PageServerLoad } from "../../$types";
import { error, redirect } from "@sveltejs/kit";
import { api_fetch_srv } from "$lib/server/utils";
import type { User } from "$lib/utils/const";
import { service_name_get_set_cache } from "./user_utils";

// This is the ordering of the HEADERS column
const HEADERS = {
    user: "User/ID",
    namemail: "Name/Mail",
    role: "Role",
    created: "Created",
};
const MOBILE_FILTER_HEADERS: (keyof typeof HEADERS)[] = ["role"];
const ROWS_PER_PAGE = 10;

export const load: PageServerLoad = async (event) => {
    const token = event.locals.credentials?.token;
    if (token) {
        const [user_resp, total_users_resp, service_names_resp] = await Promise.all([
            api_fetch_srv(event, token, `user?limit=${ROWS_PER_PAGE}`),
            api_fetch_srv(event, token, "misc/total_users"),
            service_name_get_set_cache(event, token),
            // event.fetch(api_path_server("misc/total_users")),
            // event.fetch(api_path_server("internal/service/names")),
        ]);
        if (user_resp.ok) {
            return {
                rows_per_page: ROWS_PER_PAGE,
                users: (await user_resp.json()) as User[],
                users_count: parseInt(await total_users_resp.text()),
                services: service_names_resp,
                headers: HEADERS,
                headers_filter: MOBILE_FILTER_HEADERS,
            };
        }
    }
    redirect(303, "/");
};

// users = [
//     {
//         acl: [{ resource: "store", rwx: 6 }],
//         data: { name: "myname" },
//         login: { mail: null, name: "myuser" },
//         modified_date: "2024-06-08T20:12:16.887720Z",
//         registration: {
//             created: "2024-06-08T20:12:16.887720Z",
//             created_by: "user:root",
//             mail: null,
//             name: "myformername",
//         },
//         roles: ["root"],
//         user_id: "9vf9yip5ryxcfreqf8r8",
//     },
//     {
//         acl: [],
//         data: { name: "eman" },
//         login: { mail: "example@mail.com", name: "nogin" },
//         modified_date: "2024-06-10T20:12:16.4420Z",
//         registration: {
//             created: "2024-06-08T20:12:16.84720Z",
//             created_by: "user:root",
//             mail: null,
//             name: "myformername",
//         },
//         roles: ["mod"],
//         user_id: "10ffxfp8rynchrexh8ta",
//     },
// ] as Array<User>;
