import { FormEvent, useEffect, useMemo, useState } from "react";

type Language = "fa" | "en";

type SkillTranslation = {
  language_code: string;
  label: string;
};

type Skill = {
  key: string;
  category_key: string;
  applies_to_role_group: string;
  priority: number;
  translations: SkillTranslation[];
};

type Player = {
  id: number;
  display_name: string;
  name_fa?: string | null;
  name_en?: string | null;
  role_type: string;
  appearance_score: number;
  image_url?: string | null;
  is_active: boolean;
  linked_user_id: number | null;
};

type AuthPayload = {
  token: string;
  user: {
    id: number;
    username: string;
    preferred_language: Language;
    is_admin: boolean;
    is_active: boolean;
    is_approved: boolean;
  };
  player: Player | null;
};

type PendingRegistration = {
  user: AuthPayload["user"];
  player: Player;
};

type ComparisonQuestion = {
  skill: Skill;
  player_a: Player;
  player_b: Player;
  existing_answer_count: number;
  disagreement_count: number;
};

type PlayerRating = {
  player: Player;
  overall_rating: number;
  goalkeeper_rating: number | null;
  category_ratings: Record<string, number>;
  skill_ratings: Record<string, { rating: number | null; comparisons_count: number }>;
  comparison_total: number;
  maturity: number;
};

type GeneratedTeam = {
  team_index: number;
  players: PlayerRating[];
  metrics: {
    overall: number;
    goalkeeper: number;
    categories: Record<string, number>;
    player_ids: number[];
    size: number;
  };
};

type ProgressStats = {
  answered_count: number;
  skipped_count: number;
  total_possible: number;
  completion_percent: number;
};

type ImageUploadResponse = {
  image_url: string;
};

type AdminComparison = {
  id: number;
  created_at: string;
  evaluator_user: AuthPayload["user"];
  skill: Skill;
  player_a: Player;
  player_b: Player;
  winner_player_id: number;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

const translations = {
  fa: {
    appTitle: "تیم‌ساز فوتسال",
    loginIntro: "برای دسترسی به سوال‌های مقایسه‌ای و کارت بازیکنان وارد شوید.",
    registerIntro: "اگر حساب ندارید ثبت‌نام کنید. ورود تا زمان تایید ادمین غیرفعال خواهد بود.",
    login: "ورود",
    register: "ثبت‌نام",
    registrationPending: "ثبت‌نام شما انجام شد و در انتظار تایید ادمین است.",
    registrationApproved: "ثبت‌نام تایید شد.",
    switchToRegister: "ایجاد حساب جدید",
    switchToLogin: "بازگشت به ورود",
    pendingRegistrations: "ثبت‌نام‌های در انتظار تایید",
    approveRegistration: "تایید ثبت‌نام",
    rejectRegistration: "رد ثبت‌نام",
    noPendingRegistrations: "در حال حاضر ثبت‌نام در انتظاری وجود ندارد.",
    username: "نام کاربری",
    password: "رمز عبور",
    logout: "خروج",
    account: "حساب",
    compareTitle: "سوال مقایسه‌ای",
    compareHelp: "بازیکنی را انتخاب کنید که در این مهارت بهتر است.",
    compareEmpty: "در حال حاضر سوال جدیدی برای شما وجود ندارد.",
    compareLoading: "در حال دریافت سوال...",
    compareError: "در دریافت یا ثبت سوال خطایی رخ داد.",
    compareNoticeAnswer: "در حال ثبت پاسخ...",
    compareNoticeNext: "",
    compareNoticeSkip: "سوال رد شد.",
    answeredCount: "تعداد پاسخ‌ها",
    disagreementCount: "میزان اختلاف",
    chooseBetterPlayer: "بازیکن بهتر را انتخاب کنید",
    skip: "رد کردن",
    voteTab: "رای دادن",
    rankingsTab: "رتبه‌بندی",
    accountTab: "حساب",
    editProfile: "ویرایش پروفایل",
    saveProfile: "ذخیره پروفایل",
    profileUpdated: "پروفایل به‌روز شد.",
    changePassword: "تغییر رمز عبور",
    currentPassword: "رمز عبور فعلی",
    newPassword: "رمز عبور جدید",
    confirmNewPassword: "تکرار رمز عبور جدید",
    savePassword: "ذخیره رمز عبور",
    passwordUpdated: "رمز عبور به‌روز شد.",
    passwordMismatch: "رمز عبور جدید و تکرار آن یکسان نیستند.",
    detailedCard: "کارت بازیکن",
    skillBreakdown: "جزئیات مهارت‌ها",
    close: "بستن",
    playersTab: "بازیکنان",
    ratingsTab: "رتبه‌بندی",
    teamsTab: "تیم‌ها",
    comparisonsTab: "مقایسه‌ها",
    comparisonsList: "همه مقایسه‌ها",
    evaluator: "ارزیاب",
    progress: "پیشرفت",
    answeredQuestions: "پاسخ داده‌اید",
    skippedQuestions: "رد کرده‌اید",
    players: "کارت بازیکنان",
    rankings: "رتبه‌بندی فعلی",
    rankingsHint: "این فهرست بر اساس امتیاز واقعی بازیکنان از مقایسه‌ها محاسبه شده است.",
    moreInfo: "بازیکن‌ها و رتبه‌بندی",
    overall: "امتیاز کلی",
    maturity: "اعتبار امتیاز",
    comparisonsTotal: "کل مقایسه‌ها",
    attacking: "هجومی",
    possession: "مالکیت",
    defensive: "دفاعی",
    physical: "فیزیکی",
    goalkeeping: "دروازه‌بانی",
    teamGenerator: "تولید تیم",
    teamCount: "تعداد تیم‌ها",
    playersPerTeam: "بازیکن در هر تیم",
    participants: "بازیکنان حاضر",
    goalkeepers: "دروازه‌بان‌ها",
    generateTeams: "ساخت تیم‌ها",
    regenerateTeams: "تولید دوباره تیم‌ها",
    generatedTeams: "تیم‌های ساخته‌شده",
    noTeamsYet: "هنوز تیمی ساخته نشده است.",
    chooseParticipants: "بازیکنان حاضر در این نوبت را انتخاب کنید.",
    adminPanel: "پنل ادمین",
    adminHelp: "ایجاد کاربر جدید فقط از طریق این بخش امکان‌پذیر است.",
    managePlayers: "مدیریت بازیکنان",
    createUser: "ایجاد کاربر",
    nameFa: "نام فارسی",
    nameEn: "نام انگلیسی",
    playRole: "نقش بازی",
    appearanceScore: "امتیاز حضور",
    createUserSuccess: "کاربر جدید با موفقیت ایجاد شد.",
    saveChanges: "ذخیره تغییرات",
    deletePlayer: "غیرفعال کردن بازیکن",
    deleteConfirm: "آیا از غیرفعال کردن این بازیکن و حساب کاربری او مطمئن هستید؟",
    deleteSuccess: "بازیکن غیرفعال شد.",
    cancel: "انصراف",
    playerPhoto: "عکس بازیکن",
    editPlayer: "ویرایش بازیکن",
    playerActive: "بازیکن فعال باشد",
    inactivePlayer: "غیرفعال",
    playerUpdated: "بازیکن به‌روز شد.",
    searchPlayers: "جستجوی بازیکن",
    loggedInAs: "وارد شده با",
    noLinkedPlayer: "این حساب به بازیکنی متصل نیست.",
    language: "زبان",
    persian: "فارسی",
    english: "English",
    role_goalkeeper: "دروازه‌بان",
    role_hybrid: "هیبرید",
    role_outfield: "بازیکن زمین",
  },
  en: {
    appTitle: "Futsal Team Balancer",
    loginIntro: "Log in to access comparison questions and player cards.",
    registerIntro: "Create an account if you do not have one yet. Login stays blocked until an admin approves it.",
    login: "Login",
    register: "Register",
    registrationPending: "Your registration was submitted and is waiting for admin approval.",
    registrationApproved: "Registration approved.",
    switchToRegister: "Create a new account",
    switchToLogin: "Back to login",
    pendingRegistrations: "Pending Registrations",
    approveRegistration: "Approve Registration",
    rejectRegistration: "Reject Registration",
    noPendingRegistrations: "There are no pending registrations right now.",
    username: "Username",
    password: "Password",
    logout: "Logout",
    account: "Account",
    compareTitle: "Comparison Question",
    compareHelp: "Choose the player who is better in this skill.",
    compareEmpty: "There are no new questions for you right now.",
    compareLoading: "Loading next question...",
    compareError: "There was an error while loading or submitting the question.",
    compareNoticeAnswer: "Submitting answer...",
    compareNoticeNext: "",
    compareNoticeSkip: "Question skipped.",
    answeredCount: "Answers",
    disagreementCount: "Disagreement",
    chooseBetterPlayer: "Choose the better player",
    skip: "Skip",
    voteTab: "Vote",
    rankingsTab: "Rankings",
    accountTab: "Account",
    editProfile: "Edit Profile",
    saveProfile: "Save Profile",
    profileUpdated: "Profile updated.",
    changePassword: "Change Password",
    currentPassword: "Current Password",
    newPassword: "New Password",
    confirmNewPassword: "Confirm New Password",
    savePassword: "Save Password",
    passwordUpdated: "Password updated.",
    passwordMismatch: "The new password and confirmation do not match.",
    detailedCard: "Player Card",
    skillBreakdown: "Skill Breakdown",
    close: "Close",
    playersTab: "Players",
    ratingsTab: "Ratings",
    teamsTab: "Teams",
    comparisonsTab: "Comparisons",
    comparisonsList: "All Comparisons",
    evaluator: "Evaluator",
    progress: "Progress",
    answeredQuestions: "answered",
    skippedQuestions: "skipped",
    players: "Player Cards",
    rankings: "Current Rankings",
    rankingsHint: "This ranking is computed from pairwise comparison results.",
    moreInfo: "Players and Rankings",
    overall: "Overall",
    maturity: "Rating Maturity",
    comparisonsTotal: "Total Comparisons",
    attacking: "Attacking",
    possession: "Possession",
    defensive: "Defensive",
    physical: "Physical",
    goalkeeping: "Goalkeeping",
    teamGenerator: "Team Generator",
    teamCount: "Number of Teams",
    playersPerTeam: "Players Per Team",
    participants: "Participants",
    goalkeepers: "Goalkeepers",
    generateTeams: "Generate Teams",
    regenerateTeams: "Regenerate Teams",
    generatedTeams: "Generated Teams",
    noTeamsYet: "No teams generated yet.",
    chooseParticipants: "Choose the players participating in this session.",
    adminPanel: "Admin Panel",
    adminHelp: "Creating new users is only available from this section.",
    managePlayers: "Manage Players",
    createUser: "Create User",
    nameFa: "Persian Name",
    nameEn: "English Name",
    playRole: "Playing Role",
    appearanceScore: "Appearance Score",
    createUserSuccess: "The new user was created successfully.",
    saveChanges: "Save Changes",
    deletePlayer: "Deactivate Player",
    deleteConfirm: "Are you sure you want to deactivate this player and the linked user account?",
    deleteSuccess: "Player deactivated.",
    cancel: "Cancel",
    playerPhoto: "Player Photo",
    editPlayer: "Edit Player",
    playerActive: "Player is active",
    inactivePlayer: "Inactive",
    playerUpdated: "Player updated.",
    searchPlayers: "Search players",
    loggedInAs: "Logged in as",
    noLinkedPlayer: "This account is not linked to a player.",
    language: "Language",
    persian: "فارسی",
    english: "English",
    role_goalkeeper: "Goalkeeper",
    role_hybrid: "Hybrid",
    role_outfield: "Outfield Player",
  },
} as const;

export function App() {
  const [skillCatalog, setSkillCatalog] = useState<Skill[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [ratings, setRatings] = useState<PlayerRating[]>([]);
  const [adminComparisons, setAdminComparisons] = useState<AdminComparison[]>([]);
  const [pendingRegistrations, setPendingRegistrations] = useState<PendingRegistration[]>([]);
  const [progress, setProgress] = useState<ProgressStats | null>(null);
  const [auth, setAuth] = useState<AuthPayload | null>(null);
  const [language, setLanguage] = useState<Language>("fa");
  const [userTab, setUserTab] = useState<"vote" | "rankings" | "account">("vote");
  const [adminTab, setAdminTab] = useState<"players" | "ratings" | "teams" | "comparisons">("players");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminNotice, setAdminNotice] = useState<string | null>(null);
  const [comparisonQuestion, setComparisonQuestion] = useState<ComparisonQuestion | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonSubmitting, setComparisonSubmitting] = useState<"answer" | "skip" | null>(null);
  const [comparisonNotice, setComparisonNotice] = useState<string | null>(null);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [adminCreateForm, setAdminCreateForm] = useState({
    username: "",
    password: "",
    name_fa: "",
    name_en: "",
    role_type: "outfield",
    appearance_score: 50,
    preferred_language: "fa" as Language,
    image_url: "",
  });
  const [editingPlayerId, setEditingPlayerId] = useState<number | null>(null);
  const [teamCount, setTeamCount] = useState(2);
  const [playersPerTeam, setPlayersPerTeam] = useState(4);
  const [selectedParticipantIds, setSelectedParticipantIds] = useState<number[]>([]);
  const [selectedGoalkeeperIds, setSelectedGoalkeeperIds] = useState<number[]>([]);
  const [generatedTeams, setGeneratedTeams] = useState<GeneratedTeam[]>([]);
  const [teamGenerationError, setTeamGenerationError] = useState<string | null>(null);
  const [playerSearch, setPlayerSearch] = useState("");
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [selectedPlayerCard, setSelectedPlayerCard] = useState<PlayerRating | null>(null);
  const [selfProfileForm, setSelfProfileForm] = useState({
    name_fa: "",
    name_en: "",
    role_type: "outfield",
    image_url: "",
    preferred_language: "fa" as Language,
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [playerEditForm, setPlayerEditForm] = useState({
    name_fa: "",
    name_en: "",
    role_type: "outfield",
    appearance_score: 50,
    image_url: "",
    is_active: true,
  });

  const text = translations[language];
  const dir = language === "fa" ? "rtl" : "ltr";

  useEffect(() => {
    const storedLanguage = window.localStorage.getItem("team-balancer-language");
    if (storedLanguage === "fa" || storedLanguage === "en") {
      setLanguage(storedLanguage);
    }

    const storedAuth = window.localStorage.getItem("team-balancer-auth");
    if (!storedAuth) return;

    try {
      const parsed = JSON.parse(storedAuth) as AuthPayload;
      setAuth(parsed);
      setLanguage(parsed.user.preferred_language ?? "fa");
    } catch {
      window.localStorage.removeItem("team-balancer-auth");
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("team-balancer-language", language);
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [dir, language]);

  useEffect(() => {
    if (!auth) {
      window.localStorage.removeItem("team-balancer-auth");
      setPlayers([]);
      setSkillCatalog([]);
      setRatings([]);
      setAdminComparisons([]);
      setPendingRegistrations([]);
      setProgress(null);
      setComparisonQuestion(null);
      return;
    }

    window.localStorage.setItem("team-balancer-auth", JSON.stringify(auth));
    setSelfProfileForm({
      name_fa: auth.player?.name_fa ?? "",
      name_en: auth.player?.name_en ?? auth.player?.display_name ?? "",
      role_type: auth.player?.role_type ?? "outfield",
      image_url: auth.player?.image_url ?? "",
      preferred_language: auth.user.preferred_language ?? "fa",
    });
    void loadPlayers(auth.token);
    void loadReferenceData();
    void loadRatings(auth.token);
    if (auth.user.is_admin) {
      void loadAdminComparisons(auth.token);
      void loadPendingRegistrations(auth.token);
    }
    void loadProgress(auth.token);
    if (!auth.user.is_admin && auth.player) {
      void loadNextComparison(auth.token);
    } else {
      setComparisonQuestion(null);
    }
  }, [auth]);

  useEffect(() => {
    if (!auth?.user.is_admin) return;
    const activePlayerIds = players.filter((player) => player.is_active).map((player) => player.id);
    setSelectedParticipantIds((current) => {
      if (current.length > 0) {
        return current.filter((id) => activePlayerIds.includes(id));
      }
      return activePlayerIds;
    });
  }, [auth?.user.is_admin, players]);

  const rankedPlayers = useMemo(
    () => (ratings.length > 0 ? ratings : [...players]
      .sort((left, right) => right.appearance_score - left.appearance_score)
      .map((player) => ({
        player,
        overall_rating: player.appearance_score,
        goalkeeper_rating: null,
        category_ratings: {},
        skill_ratings: {},
        comparison_total: 0,
        maturity: 0,
      }))),
    [players, ratings],
  );
  const activePlayers = useMemo(
    () => players.filter((player) => player.is_active),
    [players],
  );
  const participantRatings = useMemo(
    () => rankedPlayers.filter((item) => selectedParticipantIds.includes(item.player.id)),
    [rankedPlayers, selectedParticipantIds],
  );
  const filteredPlayers = useMemo(() => {
    const query = playerSearch.trim().toLowerCase();
    if (!query) return players;
    return players.filter((player) =>
      [player.display_name, player.name_fa ?? "", player.name_en ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [playerSearch, players]);
  const filteredRankedPlayers = useMemo(
    () => rankedPlayers.filter((item) => filteredPlayers.some((player) => player.id === item.player.id)),
    [filteredPlayers, rankedPlayers],
  );
  const sortedAdminComparisons = useMemo(
    () => [...adminComparisons].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()),
    [adminComparisons],
  );

  function roleLabel(role: string) {
    return (
      {
        goalkeeper: text.role_goalkeeper,
        hybrid: text.role_hybrid,
        outfield: text.role_outfield,
      }[role] ?? role
    );
  }

  function formatDisplayNumber(value: number) {
    return new Intl.NumberFormat(language === "fa" ? "fa-IR" : "en-US").format(value);
  }

  function displayCardScore(value: number | null | undefined) {
    if (value === null || value === undefined || Number.isNaN(value)) return "-";
    const clamped = Math.max(0, Math.min(100, value));
    const mapped = 60 + (clamped / 100) * 39;
    return formatDisplayNumber(Math.round(mapped));
  }

  function playerName(player: Player) {
    if (language === "fa") {
      return player.name_fa || player.name_en || player.display_name;
    }
    return player.name_en || player.name_fa || player.display_name;
  }

  function secondaryPlayerName(player: Player) {
    const primary = playerName(player);
    const secondary = language === "fa"
      ? player.name_en || player.display_name
      : player.name_fa || player.display_name;
    return secondary && secondary !== primary ? secondary : null;
  }

  function skillLabel(skill: Skill) {
    return (
      skill.translations.find((translation) => translation.language_code === language)?.label ??
      skill.translations.find((translation) => translation.language_code === "fa")?.label ??
      skill.key
    );
  }

  function skillLabelByKey(skillKey: string) {
    const skill = skillCatalog.find((item) => item.key === skillKey);
    if (skill) return skillLabel(skill);
    return skillKey
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function categoryLabel(categoryKey: string) {
    const labelMap: Record<string, string> = {
      attacking: text.attacking,
      possession: text.possession,
      defensive: text.defensive,
      physical: text.physical,
      goalkeeping: text.goalkeeping,
    };
    return labelMap[categoryKey] ?? categoryKey;
  }

  function isWinnerInComparison(item: AdminComparison, player: Player) {
    return item.winner_player_id === player.id;
  }

  function toggleParticipant(playerId: number) {
    setSelectedParticipantIds((current) => {
      const isSelected = current.includes(playerId);
      const next = isSelected
        ? current.filter((id) => id !== playerId)
        : [...current, playerId];
      if (isSelected) {
        setSelectedGoalkeeperIds((goalkeepers) => goalkeepers.filter((id) => id !== playerId));
      }
      return next;
    });
  }

  function toggleGoalkeeper(playerId: number) {
    setSelectedGoalkeeperIds((current) =>
      current.includes(playerId)
        ? current.filter((id) => id !== playerId)
        : [...current, playerId],
    );
  }

  function suggestedGoalkeeperIds() {
    return participantRatings
      .filter((item) => item.player.role_type === "goalkeeper" || item.player.role_type === "hybrid")
      .sort(
        (left, right) =>
          (right.goalkeeper_rating ?? right.overall_rating) - (left.goalkeeper_rating ?? left.overall_rating),
      )
      .slice(0, teamCount)
      .map((item) => item.player.id);
  }

  useEffect(() => {
    if (!auth?.user.is_admin) return;
    const suggestions = suggestedGoalkeeperIds();
    const eligible = new Set(participantRatings.map((item) => item.player.id));
    setSelectedGoalkeeperIds((current) => {
      const kept = current.filter((id) => eligible.has(id));
      const filled = [...kept];
      for (const playerId of suggestions) {
        if (!filled.includes(playerId)) {
          filled.push(playerId);
        }
        if (filled.length >= teamCount) break;
      }
      return filled.slice(0, teamCount);
    });
  }, [auth?.user.is_admin, participantRatings, teamCount]);

  async function loadPlayers(token: string) {
    const response = await fetch(`${apiBaseUrl}/api/players`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    setPlayers((await response.json()) as Player[]);
  }

  async function loadReferenceData() {
    const response = await fetch(`${apiBaseUrl}/api/reference-data`);
    if (!response.ok) return;
    const payload = (await response.json()) as { skills: Skill[] };
    setSkillCatalog(payload.skills ?? []);
  }

  async function loadAdminComparisons(token: string) {
    const response = await fetch(`${apiBaseUrl}/api/admin/comparisons`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    setAdminComparisons((await response.json()) as AdminComparison[]);
  }

  async function loadPendingRegistrations(token: string) {
    const response = await fetch(`${apiBaseUrl}/api/admin/pending-registrations`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    setPendingRegistrations((await response.json()) as PendingRegistration[]);
  }

  async function loadRatings(token: string) {
    const response = await fetch(`${apiBaseUrl}/api/ratings`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    const payload = (await response.json()) as { items: PlayerRating[] };
    setRatings(payload.items);
  }

  async function loadProgress(token: string) {
    const response = await fetch(`${apiBaseUrl}/api/progress`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    setProgress((await response.json()) as ProgressStats);
  }

  async function loadNextComparison(token: string) {
    setComparisonLoading(true);
    setComparisonError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/api/comparisons/next`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("comparison-request-failed");
      setComparisonQuestion((await response.json()) as ComparisonQuestion | null);
    } catch {
      setComparisonError(text.compareError);
    } finally {
      setComparisonLoading(false);
      setComparisonSubmitting(null);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError(null);
    const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(loginForm),
    });
    const data = await response.json();
    if (!response.ok) {
      setLoginError(data.detail ?? text.compareError);
      return;
    }
    setAuth(data as AuthPayload);
    setLanguage((data as AuthPayload).user.preferred_language ?? "fa");
    setLoginForm({ username: "", password: "" });
  }

  async function handleAdminCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth) return;
    setAdminError(null);
    setAdminNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/admin/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify(adminCreateForm),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setAdminError(data?.detail ?? text.compareError);
      return;
    }
    setAdminNotice(text.createUserSuccess);
    setAdminCreateForm({
      username: "",
      password: "",
      name_fa: "",
      name_en: "",
      role_type: "outfield",
      appearance_score: 50,
      preferred_language: language,
      image_url: "",
    });
    await loadPlayers(auth.token);
    await loadRatings(auth.token);
  }

  async function handleApproveRegistration(userId: number) {
    if (!auth) return;
    setAdminError(null);
    setAdminNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/admin/registrations/${userId}/approve`, {
      method: "POST",
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
      setAdminError(payload?.detail ?? text.compareError);
      return;
    }
    setPendingRegistrations((current) => current.filter((item) => item.user.id !== userId));
    await loadPlayers(auth.token);
    setAdminNotice(text.registrationApproved);
  }

  async function handleRejectRegistration(userId: number) {
    if (!auth) return;
    setAdminError(null);
    setAdminNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/admin/registrations/${userId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
      setAdminError(payload?.detail ?? text.compareError);
      return;
    }
    setPendingRegistrations((current) => current.filter((item) => item.user.id !== userId));
  }

  function startEditPlayer(player: Player) {
    setEditingPlayerId(player.id);
    setAdminError(null);
    setAdminNotice(null);
    setPlayerEditForm({
      name_fa: player.name_fa ?? "",
      name_en: player.name_en ?? player.display_name,
      role_type: player.role_type,
      appearance_score: player.appearance_score,
      image_url: player.image_url ?? "",
      is_active: player.is_active,
    });
  }

  function cancelEditPlayer() {
    setEditingPlayerId(null);
  }

  async function handleUpdatePlayer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth || editingPlayerId === null) return;
    setAdminError(null);
    setAdminNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/players/${editingPlayerId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify(playerEditForm),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setAdminError(data?.detail ?? text.compareError);
      return;
    }
    setAdminNotice(text.playerUpdated);
    setEditingPlayerId(null);
    await loadPlayers(auth.token);
    await loadRatings(auth.token);
  }

  async function handleDeletePlayer() {
    if (!auth || editingPlayerId === null) return;
    if (!window.confirm(text.deleteConfirm)) return;

    setAdminError(null);
    setAdminNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/players/${editingPlayerId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${auth.token}`,
      },
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setAdminError(data?.detail ?? text.compareError);
      return;
    }

    setAdminNotice(text.deleteSuccess);
    setEditingPlayerId(null);
    await loadPlayers(auth.token);
    await loadRatings(auth.token);
  }

  async function resizeImage(file: File): Promise<Blob> {
    if (!file.type.startsWith("image/")) {
      throw new Error("Only image files are allowed.");
    }

    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.src = objectUrl;

    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("Could not read image file."));
    });

    const maxSide = 800;
    const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
    const width = Math.max(1, Math.round(image.width * scale));
    const height = Math.max(1, Math.round(image.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      URL.revokeObjectURL(objectUrl);
      throw new Error("Could not process image file.");
    }

    context.drawImage(image, 0, 0, width, height);
    URL.revokeObjectURL(objectUrl);

    return await new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Could not process image file."));
            return;
          }
          resolve(blob);
        },
        "image/jpeg",
        0.82,
      );
    });
  }

  async function uploadPlayerImage(file: File): Promise<string> {
    if (!auth) {
      throw new Error(text.compareError);
    }
    const image = await resizeImage(file);
    const formData = new FormData();
    formData.append("file", image, "player-photo.jpg");
    const response = await fetch(`${apiBaseUrl}/api/uploads/player-image`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${auth.token}`,
      },
      body: formData,
    });
    const payload = (await response.json().catch(() => null)) as ImageUploadResponse | { detail?: string } | null;
    if (!response.ok || !payload || !("image_url" in payload)) {
      throw new Error(payload && "detail" in payload ? payload.detail ?? text.compareError : text.compareError);
    }
    return payload.image_url;
  }

  async function handleCreatePhotoChange(file: File | null) {
    if (!file) {
      setAdminCreateForm((current) => ({ ...current, image_url: "" }));
      return;
    }
    try {
      setAdminError(null);
      const imageUrl = await uploadPlayerImage(file);
      setAdminCreateForm((current) => ({ ...current, image_url: imageUrl }));
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : text.compareError);
    }
  }

  async function handleEditPhotoChange(file: File | null) {
    if (!file) {
      setPlayerEditForm((current) => ({ ...current, image_url: "" }));
      return;
    }
    try {
      setAdminError(null);
      const imageUrl = await uploadPlayerImage(file);
      setPlayerEditForm((current) => ({ ...current, image_url: imageUrl }));
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : text.compareError);
    }
  }

  async function handleSelfPhotoChange(file: File | null) {
    if (!file) {
      setSelfProfileForm((current) => ({ ...current, image_url: "" }));
      return;
    }
    try {
      setProfileError(null);
      const imageUrl = await uploadPlayerImage(file);
      setSelfProfileForm((current) => ({ ...current, image_url: imageUrl }));
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : text.compareError);
    }
  }

  function handleLogout() {
    setAuth(null);
    setLoginError(null);
    setAdminError(null);
    setAdminNotice(null);
    setProfileNotice(null);
    setProfileError(null);
    setPasswordNotice(null);
    setPasswordError(null);
    setComparisonQuestion(null);
    setComparisonError(null);
    setComparisonNotice(null);
    setComparisonSubmitting(null);
    setLoginForm({ username: "", password: "" });
    setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
  }

  async function handleComparisonAnswer(winnerPlayerId: number) {
    if (!auth || !comparisonQuestion || comparisonSubmitting) return;
    setComparisonError(null);
    setComparisonNotice(text.compareNoticeAnswer);
    setComparisonSubmitting("answer");
    const response = await fetch(`${apiBaseUrl}/api/comparisons`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        skill_key: comparisonQuestion.skill.key,
        player_a_id: comparisonQuestion.player_a.id,
        player_b_id: comparisonQuestion.player_b.id,
        winner_player_id: winnerPlayerId,
      }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      setComparisonError(errorData?.detail ?? text.compareError);
      setComparisonNotice(null);
      setComparisonSubmitting(null);
      return;
    }
    setComparisonNotice(text.compareNoticeNext);
    await loadNextComparison(auth.token);
    await loadRatings(auth.token);
    await loadProgress(auth.token);
  }

  async function handleSkipComparison() {
    if (!auth || !comparisonQuestion || comparisonSubmitting) return;
    setComparisonError(null);
    setComparisonNotice(text.compareNoticeSkip);
    setComparisonSubmitting("skip");
    const response = await fetch(`${apiBaseUrl}/api/comparisons/skip`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        skill_key: comparisonQuestion.skill.key,
        player_a_id: comparisonQuestion.player_a.id,
        player_b_id: comparisonQuestion.player_b.id,
      }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      setComparisonError(errorData?.detail ?? text.compareError);
      setComparisonNotice(null);
      setComparisonSubmitting(null);
      return;
    }
    await loadNextComparison(auth.token);
    await loadProgress(auth.token);
  }

  async function handleGenerateTeams(previousTeamPlayerIds: number[][] = []) {
    if (!auth) return;
    setTeamGenerationError(null);
    const response = await fetch(`${apiBaseUrl}/api/team-generation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        team_count: teamCount,
        players_per_team: playersPerTeam,
        selected_player_ids: selectedParticipantIds,
        goalkeeper_ids: selectedGoalkeeperIds,
        previous_team_player_ids: previousTeamPlayerIds,
      }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setTeamGenerationError(data?.detail ?? text.compareError);
      return;
    }
    setGeneratedTeams((data?.teams ?? []) as GeneratedTeam[]);
  }

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth || !auth.player) return;
    setProfileError(null);
    setProfileNotice(null);
    const response = await fetch(`${apiBaseUrl}/api/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify(selfProfileForm),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setProfileError(data?.detail ?? text.compareError);
      return;
    }
    const nextAuth = data as AuthPayload;
    setAuth(nextAuth);
    setLanguage(nextAuth.user.preferred_language ?? "fa");
    setProfileNotice(translations[nextAuth.user.preferred_language ?? "fa"].profileUpdated);
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth) return;
    setPasswordError(null);
    setPasswordNotice(null);
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError(text.passwordMismatch);
      return;
    }
    const response = await fetch(`${apiBaseUrl}/api/me/password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setPasswordError(data?.detail ?? text.compareError);
      return;
    }
    setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    setPasswordNotice(text.passwordUpdated);
  }

  function languageToggle(compact = false) {
    return (
      <div className={compact ? "language-toggle compact" : "language-toggle"}>
        {!compact ? <span>{text.language}</span> : null}
        <button type="button" className={language === "fa" ? "lang-btn active" : "lang-btn"} onClick={() => setLanguage("fa")}>
          {translations.fa.persian}
        </button>
        <button type="button" className={language === "en" ? "lang-btn active" : "lang-btn"} onClick={() => setLanguage("en")}>
          {translations.en.english}
        </button>
      </div>
    );
  }

  function renderFutCard(item: PlayerRating, compact = false) {
    const categoryOrder = ["attacking", "possession", "defensive", "physical"];
    const categoryEntries = categoryOrder
      .filter((key) => key in item.category_ratings)
      .map((key) => [key, item.category_ratings[key]] as const)
      .slice(0, compact ? 4 : 4);
    const overall = displayCardScore(item.overall_rating);
    const goalkeeperScore = item.goalkeeper_rating === null ? "-" : displayCardScore(item.goalkeeper_rating);
    return (
      <button
        type="button"
        className={`fc-card ${compact ? "compact" : ""}`}
        onClick={() => setSelectedPlayerCard(item)}
      >
        <div className="fc-card-top">
          <div className="fc-card-rating">
              <strong>{overall}</strong>
            <span>{text.overall}</span>
          </div>
          <div className="fc-card-role">
            <strong>{goalkeeperScore}</strong>
            <span>{text.goalkeeping}</span>
          </div>
        </div>
        <div className="fc-card-photo-wrap">
          <img className="fc-card-photo" src={item.player.image_url ?? ""} alt={playerName(item.player)} />
        </div>
        <div className="fc-card-body">
          <h3>{playerName(item.player)}</h3>
            <div className="fc-card-stats">
              {categoryEntries.map(([categoryKey, value]) => (
                <div className="fc-stat-row" key={categoryKey}>
                  <strong>{displayCardScore(value)}</strong>
                  <span>{categoryLabel(categoryKey)}</span>
                </div>
              ))}
            </div>
        </div>
      </button>
    );
  }

  if (!auth) {
    return (
      <main className={`app-shell login-shell ${language === "fa" ? "lang-fa" : "lang-en"}`} dir={dir}>
        <section className="panel login-panel">
          <div className="login-header">
            <p className="eyebrow">{text.appTitle}</p>
            {languageToggle()}
          </div>
          <h1>{text.login}</h1>
          <p className="intro">{text.loginIntro}</p>
          <form className="stack" onSubmit={handleLogin}>
            <label>
              <span>{text.username}</span>
              <input value={loginForm.username} onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))} />
            </label>
            <label>
              <span>{text.password}</span>
              <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
            </label>
            <button type="submit">{text.login}</button>
            {loginError ? <p className="error-text">{loginError}</p> : null}
          </form>
        </section>
      </main>
    );
  }

  return (
    <main
      className={`${auth.user.is_admin ? "app-shell" : "app-shell user-shell"} ${language === "fa" ? "lang-fa" : "lang-en"}`}
      dir={dir}
    >
      {auth.user.is_admin ? (
        <section className="topbar">
          <div>
            <p className="eyebrow">{text.appTitle}</p>
            <p className="session-text">{text.loggedInAs}: <strong>{auth.user.username}</strong></p>
          </div>
          <div className="topbar-actions">
            {languageToggle(false)}
            <button type="button" onClick={handleLogout}>
              {text.logout}
            </button>
          </div>
        </section>
      ) : null}

      {auth.user.is_admin ? (
        <>
          <nav className="user-tabs admin-tabs">
            <button type="button" className={adminTab === "players" ? "tab-btn active" : "tab-btn"} onClick={() => setAdminTab("players")}>{text.playersTab}</button>
            <button type="button" className={adminTab === "ratings" ? "tab-btn active" : "tab-btn"} onClick={() => setAdminTab("ratings")}>{text.ratingsTab}</button>
            <button type="button" className={adminTab === "teams" ? "tab-btn active" : "tab-btn"} onClick={() => setAdminTab("teams")}>{text.teamsTab}</button>
            <button type="button" className={adminTab === "comparisons" ? "tab-btn active" : "tab-btn"} onClick={() => setAdminTab("comparisons")}>{text.comparisonsTab}</button>
          </nav>

          {adminTab === "players" ? (
            <>
              <section className="panel-grid">
                <article className="panel">
                  <h2>{text.createUser}</h2>
                  <p className="session-text">{text.adminHelp}</p>
                  <form className="stack" onSubmit={handleAdminCreateUser}>
                    <label>
                      <span>{text.username}</span>
                      <input value={adminCreateForm.username} onChange={(event) => setAdminCreateForm((current) => ({ ...current, username: event.target.value }))} />
                    </label>
                    <label>
                      <span>{text.password}</span>
                      <input type="password" value={adminCreateForm.password} onChange={(event) => setAdminCreateForm((current) => ({ ...current, password: event.target.value }))} />
                    </label>
                    <label>
                      <span>{text.nameFa}</span>
                      <input value={adminCreateForm.name_fa} onChange={(event) => setAdminCreateForm((current) => ({ ...current, name_fa: event.target.value }))} />
                    </label>
                    <label>
                      <span>{text.nameEn}</span>
                      <input value={adminCreateForm.name_en} onChange={(event) => setAdminCreateForm((current) => ({ ...current, name_en: event.target.value }))} />
                    </label>
                    <label>
                      <span>{text.playRole}</span>
                      <select value={adminCreateForm.role_type} onChange={(event) => setAdminCreateForm((current) => ({ ...current, role_type: event.target.value }))}>
                        <option value="goalkeeper">{roleLabel("goalkeeper")}</option>
                        <option value="hybrid">{roleLabel("hybrid")}</option>
                        <option value="outfield">{roleLabel("outfield")}</option>
                      </select>
                    </label>
                    <label>
                      <span>{text.appearanceScore}</span>
                      <input type="number" min="0" max="100" value={adminCreateForm.appearance_score} onChange={(event) => setAdminCreateForm((current) => ({ ...current, appearance_score: Number(event.target.value) }))} />
                    </label>
                    <label>
                      <span>{text.playerPhoto}</span>
                      <input type="file" accept="image/*" onChange={(event) => void handleCreatePhotoChange(event.target.files?.[0] ?? null)} />
                    </label>
                    {adminCreateForm.image_url ? <img className="player-photo preview-photo" src={adminCreateForm.image_url} alt="preview" /> : null}
                    <button type="submit">{text.createUser}</button>
                    {adminNotice ? <p className="success-text">{adminNotice}</p> : null}
                    {adminError ? <p className="error-text">{adminError}</p> : null}
                  </form>
                </article>
                <article className="panel">
                  <h2>{text.pendingRegistrations}</h2>
                  {pendingRegistrations.length === 0 ? <p className="session-text">{text.noPendingRegistrations}</p> : null}
                  <div className="stack">
                    {pendingRegistrations.map((item) => (
                      <div className="selection-card" key={item.user.id}>
                        <img className="selector-photo" src={item.player.image_url ?? ""} alt={playerName(item.player)} />
                        <strong>{playerName(item.player)}</strong>
                        <small className="secondary-name">{item.user.username}</small>
                        <small className="secondary-name">{text.nameEn}: {item.player.name_en ?? "-"}</small>
                        <small className="secondary-name">{text.nameFa}: {item.player.name_fa ?? "-"}</small>
                        <small className="secondary-name">{text.playRole}: {roleLabel(item.player.role_type)}</small>
                        <small className="secondary-name">{text.language}: {item.user.preferred_language === "fa" ? text.persian : text.english}</small>
                        <div className="inline-actions">
                          <button type="button" onClick={() => void handleApproveRegistration(item.user.id)}>
                            {text.approveRegistration}
                          </button>
                          <button type="button" className="danger-button" onClick={() => void handleRejectRegistration(item.user.id)}>
                            {text.rejectRegistration}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
                <article className="panel">
                  <div className="section-head">
                    <div>
                      <h2>{text.managePlayers}</h2>
                      <p className="session-text">{players.length} {text.playersTab}</p>
                    </div>
                    {editingPlayerId === null ? (
                      <label className="search-field">
                        <span>{text.searchPlayers}</span>
                        <input value={playerSearch} onChange={(event) => setPlayerSearch(event.target.value)} />
                      </label>
                    ) : null}
                  </div>
                  {editingPlayerId === null ? (
                    <div className="skill-list">
                      {filteredPlayers.map((player) => (
                        <button type="button" key={player.id} className="edit-player-row" onClick={() => startEditPlayer(player)}>
                          <span>
                            {playerName(player)}
                            {secondaryPlayerName(player) ? <small className="secondary-name">{secondaryPlayerName(player)}</small> : null}
                            {!player.is_active ? <small className="secondary-name">{text.inactivePlayer}</small> : null}
                          </span>
                          <small>{roleLabel(player.role_type)}</small>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <form className="stack" onSubmit={handleUpdatePlayer}>
                      <label>
                        <span>{text.nameFa}</span>
                        <input value={playerEditForm.name_fa} onChange={(event) => setPlayerEditForm((current) => ({ ...current, name_fa: event.target.value }))} />
                      </label>
                      <label>
                        <span>{text.nameEn}</span>
                        <input value={playerEditForm.name_en} onChange={(event) => setPlayerEditForm((current) => ({ ...current, name_en: event.target.value }))} />
                      </label>
                      <label>
                        <span>{text.playRole}</span>
                        <select value={playerEditForm.role_type} onChange={(event) => setPlayerEditForm((current) => ({ ...current, role_type: event.target.value }))}>
                          <option value="goalkeeper">{roleLabel("goalkeeper")}</option>
                          <option value="hybrid">{roleLabel("hybrid")}</option>
                          <option value="outfield">{roleLabel("outfield")}</option>
                        </select>
                      </label>
                      <label>
                        <span>{text.appearanceScore}</span>
                        <input type="number" min="0" max="100" value={playerEditForm.appearance_score} onChange={(event) => setPlayerEditForm((current) => ({ ...current, appearance_score: Number(event.target.value) }))} />
                      </label>
                      <label>
                        <span>{text.playerPhoto}</span>
                        <input type="file" accept="image/*" onChange={(event) => void handleEditPhotoChange(event.target.files?.[0] ?? null)} />
                      </label>
                      {playerEditForm.image_url ? <img className="player-photo preview-photo" src={playerEditForm.image_url} alt="preview" /> : null}
                      <label className="checkbox-row">
                        <input type="checkbox" checked={playerEditForm.is_active} onChange={(event) => setPlayerEditForm((current) => ({ ...current, is_active: event.target.checked }))} />
                        <span>{text.playerActive}</span>
                      </label>
                      <div className="inline-actions">
                        <button type="submit">{text.saveChanges}</button>
                        <button type="button" className="danger-button" onClick={() => void handleDeletePlayer()}>
                          {text.deletePlayer}
                        </button>
                        <button type="button" className="secondary-button" onClick={cancelEditPlayer}>
                          {text.cancel}
                        </button>
                      </div>
                    </form>
                  )}
                </article>
              </section>
            </>
          ) : null}

          {adminTab === "ratings" ? (
            <section className="panel-grid roster-grid">
              <article className="panel wide-panel">
                <div className="section-head">
                  <h2>{text.players}</h2>
                  <label className="search-field">
                    <span>{text.searchPlayers}</span>
                    <input value={playerSearch} onChange={(event) => setPlayerSearch(event.target.value)} />
                  </label>
                </div>
                <div className="player-gallery ranking-gallery">
                  {filteredRankedPlayers.map((item) => renderFutCard(item, true))}
                </div>
              </article>

              <article className="panel">
                <h2>{text.rankings}</h2>
                <p className="session-text">{text.rankingsHint}</p>
                <div className="skill-list">
                  {filteredRankedPlayers.map((item, index) => (
                    <div className="skill-row" key={item.player.id}>
                      <span>{index + 1}. {playerName(item.player)}</span>
                      <strong>{displayCardScore(item.overall_rating)}</strong>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          ) : null}

          {adminTab === "teams" ? (
            <>
              <section className="panel-grid">
                <article className="panel wide-panel">
                  <h2>{text.teamGenerator}</h2>
                  <p className="session-text">{text.chooseParticipants}</p>
                  <div className="stack">
                    <label>
                      <span>{text.teamCount}</span>
                      <input type="number" min="2" max="8" value={teamCount} onChange={(event) => setTeamCount(Number(event.target.value) || 2)} />
                    </label>
                    <label>
                      <span>{text.playersPerTeam}</span>
                      <input type="number" min="1" max="10" value={playersPerTeam} onChange={(event) => setPlayersPerTeam(Number(event.target.value) || 1)} />
                    </label>
                    <div>
                      <strong>{text.participants}</strong>
                      <div className="selection-grid">
                        {activePlayers.map((player) => (
                          <label className="selection-card" key={player.id}>
                            <input
                              type="checkbox"
                              checked={selectedParticipantIds.includes(player.id)}
                              onChange={() => toggleParticipant(player.id)}
                            />
                            <img className="selector-photo" src={player.image_url ?? ""} alt={playerName(player)} />
                            <span>{playerName(player)}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="inline-actions">
                        <strong>{text.goalkeepers}</strong>
                      </div>
                      <div className="selection-grid">
                        {participantRatings.map((item) => (
                          <label className="selection-card" key={item.player.id}>
                            <input
                              type="checkbox"
                              checked={selectedGoalkeeperIds.includes(item.player.id)}
                              onChange={() => toggleGoalkeeper(item.player.id)}
                            />
                            <img className="selector-photo" src={item.player.image_url ?? ""} alt={playerName(item.player)} />
                            <span>{playerName(item.player)}</span>
                            <small className="secondary-name">{text.goalkeeping}: {displayCardScore(item.goalkeeper_rating ?? 0)}</small>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div className="inline-actions">
                      <button type="button" onClick={() => void handleGenerateTeams()}>
                        {text.generateTeams}
                      </button>
                      {generatedTeams.length > 0 ? (
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => void handleGenerateTeams(generatedTeams.map((team) => team.players.map((item) => item.player.id)))}
                        >
                          {text.regenerateTeams}
                        </button>
                      ) : null}
                      {teamGenerationError ? <p className="error-text">{teamGenerationError}</p> : null}
                    </div>
                  </div>
                </article>
              </section>
              <section className="panel-grid roster-grid">
                <article className="panel wide-panel">
                  <h2>{text.generatedTeams}</h2>
                  {generatedTeams.length === 0 ? <p className="session-text">{text.noTeamsYet}</p> : null}
                      <div className="team-grid">
                        {generatedTeams.map((team) => (
                          <div className="team-card" key={team.team_index}>
                            <h3>Team {team.team_index}</h3>
                            <p className="session-text">{text.overall}: {displayCardScore(team.metrics.overall)}</p>
                            <p className="session-text">{text.goalkeeping}: {displayCardScore(team.metrics.goalkeeper)}</p>
                            <div className="category-grid">
                              {Object.entries(team.metrics.categories).map(([categoryKey, value]) => (
                                <span className="category-pill" key={categoryKey}>
                              {categoryLabel(categoryKey)} {displayCardScore(value)}
                            </span>
                          ))}
                        </div>
                        <div className="skill-list">
                          {team.players.map((item) => (
                            <div className="skill-row" key={item.player.id}>
                              <span>{playerName(item.player)}</span>
                              <strong>{displayCardScore(item.overall_rating)}</strong>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              </section>
            </>
          ) : null}

          {adminTab === "comparisons" ? (
            <section className="panel-grid">
              <article className="panel wide-panel">
                <div className="section-head">
                  <div>
                    <h2>{text.comparisonsList}</h2>
                  </div>
                </div>
                <div className="comparison-log">
                  {sortedAdminComparisons.map((item) => (
                    <div className="comparison-log-row" key={item.id}>
                      <div className="comparison-log-head">
                        <span>{text.evaluator}: <strong>{item.evaluator_user.username}</strong></span>
                        <small>{new Date(item.created_at).toLocaleString(language === "fa" ? "fa-IR" : "en-CA")}</small>
                      </div>
                      <div className="comparison-log-skill">
                        <strong>{skillLabel(item.skill)}</strong>
                      </div>
                      <div className="comparison-log-players">
                        <div className={isWinnerInComparison(item, item.player_a) ? "comparison-log-player highlighted" : "comparison-log-player"}>
                          <img className="selector-photo" src={item.player_a.image_url ?? ""} alt={playerName(item.player_a)} />
                          <span>{playerName(item.player_a)}</span>
                        </div>
                        <div className={isWinnerInComparison(item, item.player_b) ? "comparison-log-player highlighted" : "comparison-log-player"}>
                          <img className="selector-photo" src={item.player_b.image_url ?? ""} alt={playerName(item.player_b)} />
                          <span>{playerName(item.player_b)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          ) : null}
        </>
      ) : (
        <>
          <nav className="user-tabs">
            <button type="button" className={userTab === "vote" ? "tab-btn active" : "tab-btn"} onClick={() => setUserTab("vote")}>{text.voteTab}</button>
            <button type="button" className={userTab === "rankings" ? "tab-btn active" : "tab-btn"} onClick={() => setUserTab("rankings")}>{text.rankingsTab}</button>
            <button type="button" className={userTab === "account" ? "tab-btn active" : "tab-btn"} onClick={() => setUserTab("account")}>{text.accountTab}</button>
          </nav>

          {userTab === "vote" ? (
            <section className="panel-grid">
              <article className="panel wide-panel vote-panel">
                <p className="session-text">{text.compareHelp}</p>
                {comparisonNotice && comparisonNotice !== text.compareNoticeNext ? <p className="success-text">{comparisonNotice}</p> : null}
                {comparisonError ? <p className="error-text">{comparisonError}</p> : null}
                {!comparisonLoading && !comparisonQuestion && !comparisonError ? <p className="session-text">{auth.player ? text.compareEmpty : text.noLinkedPlayer}</p> : null}
                {comparisonQuestion ? (
                  <div
                    key={`${comparisonQuestion.skill.key}-${comparisonQuestion.player_a.id}-${comparisonQuestion.player_b.id}`}
                    className={`comparison-card ${comparisonSubmitting ? "is-busy" : ""} question-enter`}
                  >
                    <div className="comparison-meta">
                      <strong>{skillLabel(comparisonQuestion.skill)}</strong>
                    </div>
                    <div className="vote-layout">
                      <button
                        type="button"
                        className="choice-card"
                        onClick={() => handleComparisonAnswer(comparisonQuestion.player_a.id)}
                        disabled={Boolean(comparisonSubmitting)}
                      >
                        <img className="player-photo" src={comparisonQuestion.player_a.image_url ?? ""} alt={playerName(comparisonQuestion.player_a)} />
                        <span className="choice-name">{playerName(comparisonQuestion.player_a)}</span>
                      </button>
                      <button
                        type="button"
                        className="choice-card"
                        onClick={() => handleComparisonAnswer(comparisonQuestion.player_b.id)}
                        disabled={Boolean(comparisonSubmitting)}
                      >
                        <img className="player-photo" src={comparisonQuestion.player_b.image_url ?? ""} alt={playerName(comparisonQuestion.player_b)} />
                        <span className="choice-name">{playerName(comparisonQuestion.player_b)}</span>
                      </button>
                    </div>
                    <div className="comparison-footer">
                      <button type="button" className="secondary-button" onClick={handleSkipComparison} disabled={Boolean(comparisonSubmitting)}>
                        {text.skip}
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            </section>
          ) : null}

          {userTab === "rankings" ? (
              <section className="panel">
                <h2>{text.rankings}</h2>
                <p className="session-text">{text.rankingsHint}</p>
                <div className="player-gallery ranking-gallery">
                  {rankedPlayers.map((item) => renderFutCard(item, true))}
                </div>
              </section>
            ) : null}

          {userTab === "account" ? (
            <section className="panel account-panel">
              <h2>{text.accountTab}</h2>
              <div className="status-grid">
                <div className="status-row">
                  <span>{text.account}</span>
                  <strong>{auth.user.username}</strong>
                </div>
                {progress ? (
                  <>
                    <div className="status-row">
                      <span>{text.answeredQuestions}</span>
                      <strong>{progress.answered_count}</strong>
                    </div>
                    <div className="status-row">
                      <span>{text.skippedQuestions}</span>
                      <strong>{progress.skipped_count}</strong>
                    </div>
                  </>
                ) : null}
              </div>
              {auth.player ? (
                <form className="stack" onSubmit={handleSaveProfile}>
                  <h3>{text.editProfile}</h3>
                  <label>
                    <span>{text.nameFa}</span>
                    <input value={selfProfileForm.name_fa} onChange={(event) => setSelfProfileForm((current) => ({ ...current, name_fa: event.target.value }))} />
                  </label>
                  <label>
                    <span>{text.nameEn}</span>
                    <input value={selfProfileForm.name_en} onChange={(event) => setSelfProfileForm((current) => ({ ...current, name_en: event.target.value }))} />
                  </label>
                  <label>
                    <span>{text.playRole}</span>
                    <select value={selfProfileForm.role_type} onChange={(event) => setSelfProfileForm((current) => ({ ...current, role_type: event.target.value }))}>
                      <option value="goalkeeper">{roleLabel("goalkeeper")}</option>
                      <option value="hybrid">{roleLabel("hybrid")}</option>
                      <option value="outfield">{roleLabel("outfield")}</option>
                    </select>
                  </label>
                  <label>
                    <span>{text.language}</span>
                    <select value={selfProfileForm.preferred_language} onChange={(event) => setSelfProfileForm((current) => ({ ...current, preferred_language: event.target.value as Language }))}>
                      <option value="fa">{translations.fa.persian}</option>
                      <option value="en">{translations.en.english}</option>
                    </select>
                  </label>
                  <label>
                    <span>{text.playerPhoto}</span>
                    <input type="file" accept="image/*" onChange={(event) => void handleSelfPhotoChange(event.target.files?.[0] ?? null)} />
                  </label>
                  {selfProfileForm.image_url ? <img className="player-photo preview-photo" src={selfProfileForm.image_url} alt="preview" /> : null}
                  <div className="account-actions">
                    <button type="submit">{text.saveProfile}</button>
                  </div>
                  {profileNotice ? <p className="success-text">{profileNotice}</p> : null}
                  {profileError ? <p className="error-text">{profileError}</p> : null}
                </form>
              ) : (
                <p className="session-text">{text.noLinkedPlayer}</p>
              )}
              <form className="stack" onSubmit={handleChangePassword}>
                <h3>{text.changePassword}</h3>
                <label>
                  <span>{text.currentPassword}</span>
                  <input
                    required
                    type="password"
                    minLength={6}
                    maxLength={128}
                    autoComplete="current-password"
                    value={passwordForm.current_password}
                    onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))}
                  />
                </label>
                <label>
                  <span>{text.newPassword}</span>
                  <input
                    required
                    type="password"
                    minLength={6}
                    maxLength={128}
                    autoComplete="new-password"
                    value={passwordForm.new_password}
                    onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))}
                  />
                </label>
                <label>
                  <span>{text.confirmNewPassword}</span>
                  <input
                    required
                    type="password"
                    minLength={6}
                    maxLength={128}
                    autoComplete="new-password"
                    value={passwordForm.confirm_password}
                    onChange={(event) => setPasswordForm((current) => ({ ...current, confirm_password: event.target.value }))}
                  />
                </label>
                <div className="account-actions">
                  <button type="submit">{text.savePassword}</button>
                  <button type="button" className="secondary-button" onClick={handleLogout}>{text.logout}</button>
                </div>
                {passwordNotice ? <p className="success-text">{passwordNotice}</p> : null}
                {passwordError ? <p className="error-text">{passwordError}</p> : null}
              </form>
            </section>
          ) : null}
        </>
      )}

      {selectedPlayerCard ? (
        <div className="player-modal-backdrop" onClick={() => setSelectedPlayerCard(null)}>
          <section className="player-modal" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="player-modal-close" onClick={() => setSelectedPlayerCard(null)}>
              {text.close}
            </button>
            <div className="player-modal-hero">
                <div className="player-modal-overall">
                  <strong>{displayCardScore(selectedPlayerCard.overall_rating)}</strong>
                  <span>{text.overall}</span>
                </div>
              <img className="player-modal-photo" src={selectedPlayerCard.player.image_url ?? ""} alt={playerName(selectedPlayerCard.player)} />
              <div className="player-modal-headline">
                <p className="eyebrow">{text.detailedCard}</p>
                <h2>{playerName(selectedPlayerCard.player)}</h2>
                <p className="session-text">{roleLabel(selectedPlayerCard.player.role_type)}</p>
                  <div className="category-grid">
                    {Object.entries(selectedPlayerCard.category_ratings).map(([categoryKey, value]) => (
                      <span className="category-pill" key={categoryKey}>
                        {categoryLabel(categoryKey)} {displayCardScore(value)}
                      </span>
                    ))}
                    {selectedPlayerCard.goalkeeper_rating !== null ? (
                    <span className="category-pill">
                      {text.goalkeeping} {displayCardScore(selectedPlayerCard.goalkeeper_rating)}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
            <div className="panel-grid player-detail-grid">
              <article className="panel">
                  <h3>{text.skillBreakdown}</h3>
                  <div className="skill-list">
                    {Object.entries(selectedPlayerCard.skill_ratings)
                      .sort((left, right) => (right[1].rating ?? -1) - (left[1].rating ?? -1))
                      .map(([skillKey, value]) => (
                        <div className="skill-row" key={skillKey}>
                          <span>{skillLabelByKey(skillKey)}</span>
                          <strong>{value.rating === null ? "-" : displayCardScore(value.rating)}</strong>
                        </div>
                      ))}
                  </div>
              </article>
              <article className="panel">
                <h3>{text.rankings}</h3>
                <div className="status-grid">
                  <div className="status-row">
                    <span>{text.maturity}</span>
                    <strong>{Math.round(selectedPlayerCard.maturity)}</strong>
                  </div>
                  <div className="status-row">
                    <span>{text.comparisonsTotal}</span>
                    <strong>{selectedPlayerCard.comparison_total}</strong>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </div>
      ) : null}

    </main>
  );
}
