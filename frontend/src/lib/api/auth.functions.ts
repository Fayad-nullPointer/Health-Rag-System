import { apiClient } from "./client";


export interface LoginPayload {
    username: string;
    password: string;
}


export interface RegisterPayload {
    username: string;
    email: string;
    password: string;
    country: string;
    first_name: string;
    last_name: string;
}



export function login(
    data: LoginPayload
) {
    return apiClient(
        "/auth/login",
        {
            method: "POST",
            body: JSON.stringify(data)
        }
    );
}



export function register(
    data:RegisterPayload
) {
    return apiClient(
        "/auth/register",
        {
            method:"POST",
            body:JSON.stringify(data)
        }
    );
}



export function logout(){
    return apiClient(
        "/auth/logout",
        {
            method:"POST"
        }
    );
}