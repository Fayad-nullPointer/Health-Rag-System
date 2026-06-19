import type { QueryClient } from "@tanstack/react-query";


export interface RouterContext {

  queryClient: QueryClient;

  auth:{
    isAuthenticated:()=>boolean;
  }

}