import { QueryClient } from "@tanstack/react-query";
import {
  createRouter,
} from "@tanstack/react-router";

import { routeTree } from "./routeTree.gen";
import { isAuthenticated } from "@/lib/auth";

// hello

import type { RouterContext } from "./router-context";


export const getRouter = () => {

 const queryClient = new QueryClient();


 return createRouter({

   routeTree,

   context:{
     queryClient,
     auth:{
       isAuthenticated,
     },
   } satisfies RouterContext,

 });

};