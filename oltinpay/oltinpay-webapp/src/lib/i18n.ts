export const translations = {
  uz: {
    // Common
    loading: 'Yuklanmoqda...',
    save: 'Saqlash',
    cancel: 'Bekor qilish',
    confirm: 'Tasdiqlash',
    back: 'Orqaga',

    // Language selector
    selectLanguage: 'Tilni tanlang',

    // Wallet
    hello: 'Salom',
    wallet: 'Hamyon',
    exchange: 'Birja',
    staking: 'Steyking',
    profile: 'Profil',
    send: 'Yuborish',
    receive: 'Qabul qilish',
    recentTransactions: 'Oxirgi operatsiyalar',
    noTransactions: 'Hozircha operatsiyalar yoq',

    // Exchange
    goldPrice: 'OLTIN narxi',
    buy: 'Sotib olish',
    sell: 'Sotish',
    amount: 'Miqdor',

    // Staking
    annualYield: 'Yillik daromad',
    lockPeriod: 'kun lock davri',
    staked: 'Steykingda',
    rewards: 'Mukofotlar',
    stake: 'Steykinga qoyish',
    rewardsInfo: 'Mukofotlar har kuni 07:00 da hisoblanadi',

    // Send
    sendOltin: 'OLTIN yuborish',
    recipient: 'Qabul qiluvchi',
    searchPlaceholder: '@username yoki OltinPay ID',
    available: 'Mavjud',
    commission: 'Komissiya',
    continue: 'Davom etish',

    // Profile
    language: 'Til',
    favorites: 'Sevimli kontaktlar',
    allOperations: 'Barcha operatsiyalar',
    about: 'Ilova haqida',
    aylinAssistant: 'Aylin yordamchi',
  },

  ru: {
    // Common
    loading: 'Загрузка...',
    save: 'Сохранить',
    cancel: 'Отмена',
    confirm: 'Подтвердить',
    back: 'Назад',

    // Language selector
    selectLanguage: 'Выберите язык',

    // Wallet
    hello: 'Привет',
    wallet: 'Кошелёк',
    exchange: 'Биржа',
    staking: 'Стейкинг',
    profile: 'Профиль',
    send: 'Отправить',
    receive: 'Получить',
    recentTransactions: 'Последние операции',
    noTransactions: 'Пока нет операций',

    // Exchange
    goldPrice: 'Цена OLTIN',
    buy: 'Купить',
    sell: 'Продать',
    amount: 'Сумма',

    // Staking
    annualYield: 'Годовой доход',
    lockPeriod: 'дней блокировки',
    staked: 'В стейкинге',
    rewards: 'Награды',
    stake: 'Застейкать',
    rewardsInfo: 'Награды начисляются ежедневно в 07:00',

    // Send
    sendOltin: 'Отправить OLTIN',
    recipient: 'Получатель',
    searchPlaceholder: '@username или OltinPay ID',
    available: 'Доступно',
    commission: 'Комиссия',
    continue: 'Продолжить',

    // Profile
    language: 'Язык',
    favorites: 'Избранные контакты',
    allOperations: 'Все операции',
    about: 'О приложении',
    aylinAssistant: 'Помощник Aylin',
  },

  en: {
    // Common
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    back: 'Back',

    // Language selector
    selectLanguage: 'Select language',

    // Wallet
    hello: 'Hello',
    wallet: 'Wallet',
    exchange: 'Exchange',
    staking: 'Staking',
    profile: 'Profile',
    send: 'Send',
    receive: 'Receive',
    recentTransactions: 'Recent transactions',
    noTransactions: 'No transactions yet',

    // Exchange
    goldPrice: 'OLTIN price',
    buy: 'Buy',
    sell: 'Sell',
    amount: 'Amount',

    // Staking
    annualYield: 'Annual yield',
    lockPeriod: 'days lock period',
    staked: 'Staked',
    rewards: 'Rewards',
    stake: 'Stake',
    rewardsInfo: 'Rewards are calculated daily at 07:00',

    // Send
    sendOltin: 'Send OLTIN',
    recipient: 'Recipient',
    searchPlaceholder: '@username or OltinPay ID',
    available: 'Available',
    commission: 'Commission',
    continue: 'Continue',

    // Profile
    language: 'Language',
    favorites: 'Favorite contacts',
    allOperations: 'All operations',
    about: 'About',
    aylinAssistant: 'Aylin assistant',
  },
} as const;

export type Language = keyof typeof translations;
export type TranslationKey = keyof typeof translations.uz;
