const API_URL = import.meta.env.VITE_API_URL;


export async function apiClient<T>(
    endpoint:string,
    options?:RequestInit
):Promise<T>{


 const token =
    localStorage.getItem("access_token");


 const response =
    await fetch(
        `${API_URL}${endpoint}`,
        {

        headers:{
            "Content-Type":"application/json",

            ...(token && {
              Authorization:
              `Bearer ${token}`
            }),

            ...options?.headers
        },

        credentials:"include",

        ...options

        }
    );


 if(!response.ok){

    const error =
       await response.json()
       .catch(()=>({}));

    throw new Error(
       error.detail || "API Error"
    );
 }


 return response.json();

}