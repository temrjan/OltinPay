const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.oltinpay.com/api/v1';

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
      throw new Error(error.detail || 'Request failed');
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

  async searchUsers(q: string) {
    return this.request<any[]>(`/users/search?q=${encodeURIComponent(q)}`);
  }

  // Balances
  async getBalances() {
    return this.request<any>('/balances');
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

  // Exchange
  async getOrderbook() {
    return this.request<any>('/exchange/orderbook');
  }

  async getPrice() {
    return this.request<any>('/exchange/price');
  }

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

  // Aylin
  async chat(message: string) {
    return this.request<{ response: string; sources: any[] }>('/aylin/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }
}

export const api = new ApiClient();
