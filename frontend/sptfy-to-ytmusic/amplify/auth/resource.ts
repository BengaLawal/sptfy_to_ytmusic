import { referenceAuth } from '@aws-amplify/backend';

/**
 * Define and configure your auth resource
 * @see https://docs.amplify.aws/gen2/build-a-backend/auth
 */
export const auth = referenceAuth({
  userPoolId: import.meta.env.VITE_USER_POOL_ID as string,
  identityPoolId: import.meta.env.VITE_IDENTITY_POOL_ID as string,
  authRoleArn: import.meta.env.VITE_AUTH_ROLE_ARN as string,
  unauthRoleArn: import.meta.env.VITE_UNAUTH_ROLE_ARN as string,
  userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID as string,
});
