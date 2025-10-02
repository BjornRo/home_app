// import type { LoadEvent } from "@sveltejs/kit";
// import type { PageLoad, PageLoadEvent } from "./$types";
// import { api_path, decode_jwt } from "$lib/utils/func";
// import type { JWTStrToken, NewToken } from "$lib/utils/const";

// export const csr = true;
// export const ssr = false;

// // Assume user store HttpOnly cookie
// const fetch_token = async (event: PageLoadEvent): Promise<JWTStrToken | null> => {
//     const { fetch } = event;
//     const response = await fetch(api_path("auth/token"), {
//         method: "GET",
//         credentials: "include",
//     });
//     if (!response.ok) {
//         return null;
//     }

//     const token = (await response.json()) as NewToken;
//     return { auth: token.access_token, ...decode_jwt(token.access_token) };
// };

// export const load: PageLoad = async (event) => {
//     if (event.data.token === undefined) {
//         event.data.token = (await fetch_token(event)) ?? undefined;
//     }
// };

