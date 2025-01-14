import { referenceAuth } from '@aws-amplify/backend';

/**
 * Define and configure your auth resource
 * @see https://docs.amplify.aws/gen2/build-a-backend/auth
 */
const getUserPoolId = () => process.env.VITE_USER_POOL_ID || '';
const getIdentityPoolId = () => process.env.VITE_IDENTITY_POOL_ID || '';
const getAuthRoleArn = () => process.env.VITE_AUTH_ROLE_ARN || '';
const getUnauthRoleArn = () => process.env.VITE_UNAUTH_ROLE_ARN || '';
const getUserPoolClientId = () => process.env.VITE_USER_POOL_CLIENT_ID || '';

export const auth = referenceAuth({
  userPoolId: getUserPoolId(),
  identityPoolId: getIdentityPoolId(),
  authRoleArn: getAuthRoleArn(),
  unauthRoleArn: getUnauthRoleArn(),
  userPoolClientId: getUserPoolClientId(),
});
