import type { PageServerLoad } from "../../../$types";
import { error, redirect, type RequestEvent } from "@sveltejs/kit";
import { service_name_get_set_cache } from "../user_utils";

const ROWS_PER_PAGE = 10;

export const load: PageServerLoad = async (event: RequestEvent) => {
    const token = event.locals.credentials?.token;
    if (token) {
        return {
            rows_per_page: ROWS_PER_PAGE,
            services: await service_name_get_set_cache(event, token),
        };
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
