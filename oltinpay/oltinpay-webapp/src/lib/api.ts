import type {
  BalancesResponse,
  QuoteResponse,
  RatesResponse,
  Transaction,
  UserLookupResult,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.oltinpay.com/api/v1';

/** Error carrying the HTTP status so callers can branch on it (e.g. 409 vs 400). */
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
  }
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(response.status, error.detail || 'Request failed');
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async authenticate(initData: string) {
    return this.request<{ access_token: string; user: any; is_new: boolean }>(
      '/auth/telegram',
      {
        method: 'POST',
        body: JSON.stringify({ init_data: initData }),
      }
    );
  }

  // Users
  async getMe() {
    return this.request<any>('/users/me');
  }

  async updateMe(data: { language?: string }) {
    return this.request<any>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async setOltinId(oltin_id: string) {
    return this.request<any>('/users/oltin-id', {
      method: 'POST',
      body: JSON.stringify({ oltin_id }),
    });
  }

  // Bind the non-custodial wallet address to the current user (first call wins;
  // idempotent 200 if the same address is already bound, 409 if a different one).
  async registerWallet(wallet_address: string) {
    return this.request<{ wallet_address: string | null }>('/users/wallet', {
      method: 'POST',
      body: JSON.stringify({ wallet_address }),
    });
  }

  async searchUsers(q: string) {
    return this.request<any[]>(`/users/search?q=${encodeURIComponent(q)}`);
  }

  // Resolve a recipient oltin_id to their wallet address for a signed transfer.
  async lookupUser(oltin_id: string) {
    return this.request<UserLookupResult>(
      `/users/lookup?oltin_id=${encodeURIComponent(oltin_id)}`
    );
  }

  // Balances
  async getBalances() {
    return this.request<BalancesResponse>('/balances');
  }

  // On-chain transaction feed (indexer-backed). Requires a registered wallet;
  // the backend returns 400 if wallet_address is unset — callers show empty state.
  async getTransactions() {
    return this.request<Transaction[]>('/transactions');
  }

  async internalTransfer(data: {
    from_account: string;
    to_account: string;
    currency: string;
    amount: number;
  }) {
    return this.request<any>('/balances/transfer', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Welcome bonus (demo balance)
  async getWelcomeStatus() {
    return this.request<{
      claimed: boolean;
      tx_hash: string | null;
      claimed_at: string | null;
    }>('/welcome/status');
  }

  async claimWelcome() {
    return this.request<{
      tx_hash: string;
      amount_wei: string;
      wallet_address: string;
      claimed_at: string;
    }>('/welcome/claim', { method: 'POST' });
  }

  // Transfers
  async createTransfer(to_oltin_id: string, amount: number) {
    return this.request<any>('/transfers', {
      method: 'POST',
      body: JSON.stringify({ to_oltin_id, amount }),
    });
  }

  async getTransfers(limit = 20, offset = 0) {
    return this.request<any[]>(`/transfers?limit=${limit}&offset=${offset}`);
  }

  // Staking
  async getStaking() {
    return this.request<any>('/staking');
  }

  async stakingDeposit(amount: number) {
    return this.request<any>('/staking/deposit', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  }

  async stakingWithdraw(amount: number) {
    return this.request<any>('/staking/withdraw', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  }

  async getStakingRewards() {
    return this.request<any[]>('/staking/rewards');
  }

  // Exchange price + quote (por module, feed-derived, UZS). /rates is public;
  // /quote is auth-gated — request() attaches the bearer token automatically.
  async getRates() {
    return this.request<RatesResponse>('/rates');
  }

  async getQuote(side: 'buy' | 'sell', amount: string) {
    return this.request<QuoteResponse>(
      `/quote?side=${side}&amount=${encodeURIComponent(amount)}`
    );
  }

  // Legacy orders
  async createOrder(data: {
    side: 'buy' | 'sell';
    type: 'limit' | 'market';
    price?: number;
    quantity: number;
  }) {
    return this.request<any>('/exchange/orders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getOrders(status?: string) {
    const params = status ? `?status=${status}` : '';
    return this.request<any[]>(`/exchange/orders${params}`);
  }

  async cancelOrder(orderId: string) {
    return this.request<void>(`/exchange/orders/${orderId}`, {
      method: 'DELETE',
    });
  }

  async getTrades(limit = 50) {
    return this.request<any[]>(`/exchange/trades?limit=${limit}`);
  }

  // Contacts
  async getRecentContacts() {
    return this.request<any[]>('/contacts/recent');
  }

  async getFavorites() {
    return this.request<any[]>('/contacts/favorites');
  }

  async addFavorite(oltin_id: string) {
    return this.request<any>('/contacts/favorites', {
      method: 'POST',
      body: JSON.stringify({ oltin_id }),
    });
  }

  async removeFavorite(id: string) {
    return this.request<void>(`/contacts/favorites/${id}`, {
      method: 'DELETE',
    });
  }
}

export const api = new ApiClient();
