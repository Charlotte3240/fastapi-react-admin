import type { RunTimeLayoutConfig } from '@umijs/max';
import { history } from '@umijs/max';
import type { CurrentUser } from './access';
import { api } from './services/api';

export async function getInitialState(): Promise<{ currentUser?: CurrentUser }> {
  const token = sessionStorage.getItem('access_token');
  if (!token) return {};
  try {
    const user = await api.me();
    return {
      currentUser: {
        id: user.id,
        displayName: user.display_name,
        permissions: user.permissions,
        isSuperuser: user.is_superuser,
      },
    };
  } catch {
    sessionStorage.removeItem('access_token');
    return {};
  }
}

export const layout: RunTimeLayoutConfig = ({ initialState }) => ({
  onPageChange: () => {
    const publicPaths = ['/login', '/bootstrap'];
    if (!initialState?.currentUser && !publicPaths.includes(location.pathname)) {
      history.push('/login');
    }
  },
});
