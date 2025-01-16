import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";




const LangString = z.union([z.array(z.string()), z.string()]);

export const schemas = {
	LangString,
};

const endpoints = makeApi([
	{
		method: "post",
		path: "/admin/auth/:userId",
		alias: "postAdminauthUserId",
		description: `Perform login/logout with userid/password. Returns a JWT token.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ password: z.string() }).partial().passthrough()
			},
			{
				name: "userId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string(), token: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `User not found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "delete",
		path: "/admin/auth/:userId",
		alias: "deleteAdminauthUserId",
		description: `Logout from system`,
		requestFormat: "json",
		response: z.void(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.void()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.void()
			},
		]
	},
	{
		method: "put",
		path: "/admin/datamodel/:project/ressource",
		alias: "putAdmindatamodelProjectressource",
		description: `Creates a new ressource in the database`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ iri: z.string(), superclass: z.string().optional(), label: LangString.optional(), comment: LangString.optional(), closed: z.boolean().optional(), hasProperty: z.array(z.unknown()).optional() }).passthrough()
			},
			{
				name: "project",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 409,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "put",
		path: "/admin/permissionset/:definedByProject/:permissionsetid",
		alias: "putAdminpermissionsetDefinedByProjectPermissionsetid",
		description: `Creates a new permissionset in the database`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ label: LangString, comment: LangString, givesPermission: z.enum(["DATA_RESTRICTED", "DATA_VIEW", "DATA_EXTEND", "DATA_UPDATE", "DATA_DELETE", "DATA_PERMISSIONS"]) }).partial().passthrough()
			},
			{
				name: "definedByProject",
				type: "Path",
				schema: z.string()
			},
			{
				name: "permissionsetid",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 409,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "delete",
		path: "/admin/permissionset/:definedByProject/:permissionsetid",
		alias: "deleteAdminpermissionsetDefinedByProjectPermissionsetid",
		description: `The user that has the rights (given by his token) deletes a permissionset`,
		requestFormat: "json",
		parameters: [
			{
				name: "definedByProject",
				type: "Path",
				schema: z.string()
			},
			{
				name: "permissionsetid",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "get",
		path: "/admin/permissionset/:definedByProject/:permissionsetid",
		alias: "getAdminpermissionsetDefinedByProjectPermissionsetid",
		description: `The user that has the rights (given by his token) gets Information about a permissionset`,
		requestFormat: "json",
		parameters: [
			{
				name: "definedByProject",
				type: "Path",
				schema: z.string()
			},
			{
				name: "permissionsetid",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ permisionsetid: z.string(), creation: z.string(), contributor: z.string(), modified: z.string(), label: LangString, comment: LangString, givesPermission: z.string(), definedByProject: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "post",
		path: "/admin/permissionset/:definedByProject/:permissionsetid",
		alias: "postAdminpermissionsetDefinedByProjectPermissionsetid",
		description: `The user that has the rights (given by his token) modifies a permissionset`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ label: z.union([LangString, z.object({ add: LangString, del: LangString }).partial().passthrough()]), comment: z.union([LangString, z.object({ add: LangString, del: LangString }).partial().passthrough()]), givesPermission: z.union([z.array(z.string()), z.object({ add: z.array(z.enum(["DATA_RESTRICTED", "DATA_VIEW", "DATA_EXTEND", "DATA_UPDATE", "DATA_DELETE", "DATA_PERMISSIONS"])), del: z.array(z.array(z.enum(["DATA_RESTRICTED", "DATA_VIEW", "DATA_EXTEND", "DATA_UPDATE", "DATA_DELETE", "DATA_PERMISSIONS"]))) }).partial().passthrough()]) }).partial().passthrough()
			},
			{
				name: "definedByProject",
				type: "Path",
				schema: z.string()
			},
			{
				name: "permissionsetid",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "get",
		path: "/admin/permissionset/search",
		alias: "getAdminpermissionsetsearch",
		description: `The user that has the rights (given by his token) searches for given parameters in permissionsets`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ label: z.string(), definedByProject: z.string(), givesPermission: z.string() }).partial().passthrough()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "put",
		path: "/admin/project/:projectId",
		alias: "putAdminprojectProjectId",
		description: `Creates a new project in the database`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ projectIri: z.string(), label: LangString, comment: LangString, namespaceIri: z.string(), projectStart: z.string(), projectEnd: z.string() }).partial().passthrough()
			},
			{
				name: "projectId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 409,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "delete",
		path: "/admin/project/:projectId",
		alias: "deleteAdminprojectProjectId",
		description: `The user that has the rights (given by his token) deletes a project`,
		requestFormat: "json",
		parameters: [
			{
				name: "projectId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "get",
		path: "/admin/project/:projectId",
		alias: "getAdminprojectProjectId",
		description: `The user that has the rights (given by his token) gets Information about a project`,
		requestFormat: "json",
		parameters: [
			{
				name: "projectId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ project: z.string(), creation: z.string(), modified: z.string(), label: LangString, comment: LangString, message: z.string(), shortName: z.string(), "namespace IRI": z.string(), "project start": z.string(), "project end": z.string() }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "post",
		path: "/admin/project/:projectId",
		alias: "postAdminprojectProjectId",
		description: `The user that has the rights (given by his token) modifies a project`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ label: z.union([LangString, z.object({ add: LangString, del: LangString }).partial().passthrough()]), comment: z.union([LangString, z.object({ add: LangString, del: LangString }).partial().passthrough()]), projectStart: z.string(), projectEnd: z.string() }).partial().passthrough()
			},
			{
				name: "projectId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "get",
		path: "/admin/project/search",
		alias: "getAdminprojectsearch",
		description: `The user that has the rights (given by his token) searches for given parameters in projects`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ label: z.string(), comment: z.string() }).partial().passthrough()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "put",
		path: "/admin/user/:userId",
		alias: "putAdminuserUserId",
		description: `Create a new user with the given data`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ givenName: z.string(), familyName: z.string(), email: z.string().optional(), password: z.string().min(8), isActive: z.boolean().optional(), userIri: z.string().optional(), inProjects: z.array(z.object({ project: z.string(), permissions: z.array(z.enum(["ADMIN_OLDAP", "ADMIN_USERS", "ADMIN_PERMISSION_SETS", "ADMIN_RESOURCES", "ADMIN_MODEL", "ADMIN_CREATE"])) }).partial().passthrough()).optional(), hasPermissions: z.array(z.string()).optional() }).passthrough()
			},
			{
				name: "userId",
				type: "Path",
				schema: z.string().max(32)
			},
		],
		response: z.object({ message: z.string(), userIri: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Connection failed`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 409,
				description: `Userid or useriri already exists`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.void()
			},
		]
	},
	{
		method: "delete",
		path: "/admin/user/:userId",
		alias: "deleteAdminuserUserId",
		description: `The user that has the rights (given by his token) deletes another user`,
		requestFormat: "json",
		parameters: [
			{
				name: "userId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "get",
		path: "/admin/user/:userId",
		alias: "getAdminuserUserId",
		description: `Get all information about a user`,
		requestFormat: "json",
		parameters: [
			{
				name: "userId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ userIri: z.string(), userId: z.string(), family_name: z.string(), given_name: z.string(), email: z.string(), is_active: z.boolean(), in_projects: z.array(z.object({ project: z.string(), permissions: z.array(z.string()) }).partial().passthrough()), has_permissions: z.array(z.string()) }).partial().passthrough(),
		errors: [
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Not Found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
		]
	},
	{
		method: "post",
		path: "/admin/user/:userId",
		alias: "postAdminuserUserId",
		description: `Modify value(s) of a user definition.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ givenName: z.string(), familyName: z.string(), email: z.string(), password: z.string(), isActive: z.boolean(), inProjects: z.array(z.object({ project: z.string(), permissions: z.union([z.array(z.string()), z.object({ add: z.array(z.string()), del: z.array(z.string()) }).partial().passthrough()]) }).partial().passthrough()), hasPermissions: z.union([z.array(z.string()), z.object({ add: z.array(z.string()), del: z.array(z.string()) }).partial().passthrough()]) }).partial().passthrough()
			},
			{
				name: "userId",
				type: "Path",
				schema: z.string()
			},
		],
		response: z.object({ message: z.string() }).partial().passthrough(),
		errors: [
			{
				status: 400,
				description: `Several Errors that involve bad requests`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 403,
				description: `Unauthorized`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 404,
				description: `Userid not found`,
				schema: z.object({ message: z.string() }).partial().passthrough()
			},
			{
				status: 500,
				description: `Internal Server error. Should not be reachable`,
				schema: z.void()
			},
		]
	},
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
    return new Zodios(baseUrl, endpoints, options);
}
