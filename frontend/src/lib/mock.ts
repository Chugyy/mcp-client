export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

export interface AgentCapability {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
}

export interface Agent {
  id: string;
  name: string;
  system_prompt: string;
  description?: string;
  avatar?: string;
  tags?: string[];
  created_at: string;
  documents_count?: number;
  enabled?: boolean;
  capabilities?: AgentCapability[];
}

export interface TeamAgent {
  agent_id: string;
  enabled: boolean;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  system_prompt: string;
  agents: TeamAgent[];
  created_at: string;
  enabled?: boolean;
}

export interface Chat {
  id: string;
  user_id: number;
  agent_id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface MCPServer {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  tools: MCPTool[];
}

export interface MCPTool {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  server_id: string;
}

export interface ValidationItem {
  id: string;
  title: string;
  description: string;
  source: string;
  process: string;
  agent?: string;
  user: string;
  created_at: string;
  status: 'pending' | 'validated' | 'cancelled' | 'feedback';
}

// Mock user
const mockUser: User = {
  id: "1",
  email: "admin@admin.admin",
  name: "Admin User",
  avatar: undefined,
};

// Mock agents
const mockAgents: Agent[] = [
  {
    id: "1",
    name: "GPT-4 Assistant",
    system_prompt: "You are a helpful AI assistant.",
    description: "General purpose AI assistant using GPT-4",
    tags: ["general", "gpt-4"],
    created_at: new Date().toISOString(),
    documents_count: 0,
    enabled: true,
    capabilities: [
      { id: "1", title: "Web Search", description: "Search the web for information", enabled: true },
      { id: "2", title: "File Access", description: "Read and write files", enabled: true },
      { id: "3", title: "Code Execution", description: "Execute code snippets", enabled: false },
    ],
  },
  {
    id: "2",
    name: "Code Expert",
    system_prompt: "You are an expert programmer.",
    description: "Specialized in code review and debugging",
    tags: ["code", "development"],
    created_at: new Date().toISOString(),
    documents_count: 3,
    enabled: true,
    capabilities: [
      { id: "4", title: "Code Execution", description: "Execute code snippets", enabled: true },
      { id: "5", title: "File Access", description: "Read and write files", enabled: true },
      { id: "6", title: "API Calls", description: "Make external API calls", enabled: true },
    ],
  },
];

// Mock chats
const mockChats: Chat[] = [
  {
    id: "1",
    user_id: 1,
    agent_id: "1",
    title: "General conversation",
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "2",
    user_id: 1,
    agent_id: "2",
    title: "Debug JavaScript errors",
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "3",
    user_id: 1,
    agent_id: "1",
    title: "Travel recommendations for Paris",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "4",
    user_id: 1,
    agent_id: "2",
    title: "React best practices",
    created_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: "5",
    user_id: 1,
    agent_id: "1",
    title: "Recipe for chocolate cake",
    created_at: new Date(Date.now() - 900000).toISOString(),
  },
  {
    id: "6",
    user_id: 1,
    agent_id: "2",
    title: "API integration help",
    created_at: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: "7",
    user_id: 1,
    agent_id: "1",
    title: "Book recommendations",
    created_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: "8",
    user_id: 1,
    agent_id: "2",
    title: "Optimize database queries",
    created_at: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: "9",
    user_id: 1,
    agent_id: "1",
    title: "How to learn Python",
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
  {
    id: "10",
    user_id: 1,
    agent_id: "2",
    title: "CSS Grid vs Flexbox",
    created_at: new Date(Date.now() - 259200000).toISOString(),
  },
  {
    id: "11",
    user_id: 1,
    agent_id: "1",
    title: "Weekend activity ideas",
    created_at: new Date(Date.now() - 345600000).toISOString(),
  },
  {
    id: "12",
    user_id: 1,
    agent_id: "2",
    title: "Docker setup for Node.js",
    created_at: new Date(Date.now() - 432000000).toISOString(),
  },
  {
    id: "13",
    user_id: 1,
    agent_id: "1",
    title: "Gift ideas for birthday",
    created_at: new Date(Date.now() - 518400000).toISOString(),
  },
  {
    id: "14",
    user_id: 1,
    agent_id: "2",
    title: "TypeScript vs JavaScript",
    created_at: new Date(Date.now() - 604800000).toISOString(),
  },
  {
    id: "15",
    user_id: 1,
    agent_id: "1",
    title: "Healthy breakfast recipes",
    created_at: new Date(Date.now() - 691200000).toISOString(),
  },
  {
    id: "16",
    user_id: 1,
    agent_id: "2",
    title: "Git branching strategies",
    created_at: new Date(Date.now() - 777600000).toISOString(),
  },
  {
    id: "17",
    user_id: 1,
    agent_id: "1",
    title: "Movie recommendations 2024",
    created_at: new Date(Date.now() - 864000000).toISOString(),
  },
  {
    id: "18",
    user_id: 1,
    agent_id: "2",
    title: "REST API design principles",
    created_at: new Date(Date.now() - 950400000).toISOString(),
  },
  {
    id: "19",
    user_id: 1,
    agent_id: "1",
    title: "Meditation techniques",
    created_at: new Date(Date.now() - 1036800000).toISOString(),
  },
  {
    id: "20",
    user_id: 1,
    agent_id: "2",
    title: "SQL query optimization",
    created_at: new Date(Date.now() - 1123200000).toISOString(),
  },
  {
    id: "21",
    user_id: 1,
    agent_id: "1",
    title: "Photography tips for beginners",
    created_at: new Date(Date.now() - 1209600000).toISOString(),
  },
  {
    id: "22",
    user_id: 1,
    agent_id: "2",
    title: "Microservices architecture",
    created_at: new Date(Date.now() - 1296000000).toISOString(),
  },
  {
    id: "23",
    user_id: 1,
    agent_id: "1",
    title: "Workout routine at home",
    created_at: new Date(Date.now() - 1382400000).toISOString(),
  },
  {
    id: "24",
    user_id: 1,
    agent_id: "2",
    title: "Redux vs Context API",
    created_at: new Date(Date.now() - 1468800000).toISOString(),
  },
  {
    id: "25",
    user_id: 1,
    agent_id: "1",
    title: "Language learning strategies",
    created_at: new Date(Date.now() - 1555200000).toISOString(),
  },
  {
    id: "26",
    user_id: 1,
    agent_id: "2",
    title: "Authentication best practices",
    created_at: new Date(Date.now() - 1641600000).toISOString(),
  },
  {
    id: "27",
    user_id: 1,
    agent_id: "1",
    title: "Gardening tips for spring",
    created_at: new Date(Date.now() - 1728000000).toISOString(),
  },
  {
    id: "28",
    user_id: 1,
    agent_id: "2",
    title: "GraphQL vs REST",
    created_at: new Date(Date.now() - 1814400000).toISOString(),
  },
  {
    id: "29",
    user_id: 1,
    agent_id: "1",
    title: "Budget travel tips",
    created_at: new Date(Date.now() - 1900800000).toISOString(),
  },
  {
    id: "30",
    user_id: 1,
    agent_id: "2",
    title: "Testing strategies in React",
    created_at: new Date(Date.now() - 1987200000).toISOString(),
  },
];

// Mock teams
const mockTeams: Team[] = [
  {
    id: "1",
    name: "Development Team",
    description: "Team specialized in software development and code review",
    tags: ["development", "code"],
    system_prompt: "You are the team leader coordinating development tasks.",
    agents: [
      { agent_id: "2", enabled: true },
    ],
    created_at: new Date().toISOString(),
    enabled: true,
  },
  {
    id: "2",
    name: "General Support",
    description: "Team for general user assistance and information",
    tags: ["support", "general"],
    system_prompt: "You lead a support team. Coordinate responses efficiently.",
    agents: [
      { agent_id: "1", enabled: true },
      { agent_id: "2", enabled: false },
    ],
    created_at: new Date().toISOString(),
    enabled: true,
  },
];

// Mock messages
const mockMessages: Record<string, Message[]> = {
  "1": [
    {
      id: "1",
      chat_id: "1",
      role: "user",
      content: "Hello!",
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: "2",
      chat_id: "1",
      role: "assistant",
      content: "Hi! How can I help you today?",
      created_at: new Date(Date.now() - 86400000 + 1000).toISOString(),
    },
  ],
  "2": [
    {
      id: "3",
      chat_id: "2",
      role: "user",
      content: "I'm getting a TypeError: Cannot read property 'map' of undefined in my React component",
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      id: "4",
      chat_id: "2",
      role: "assistant",
      content: "This error typically occurs when you try to use `.map()` on a variable that is undefined. Here are a few solutions:\n\n1. **Check initial state**: Make sure your state is initialized as an empty array:\n```javascript\nconst [items, setItems] = useState([]);\n```\n\n2. **Add optional chaining**:\n```javascript\n{items?.map(item => <div key={item.id}>{item.name}</div>)}\n```\n\n3. **Use a conditional render**:\n```javascript\n{items && items.map(item => <div key={item.id}>{item.name}</div>)}\n```\n\nCould you share your code so I can provide more specific help?",
      created_at: new Date(Date.now() - 7200000 + 2000).toISOString(),
    },
  ],
  "3": [
    {
      id: "5",
      chat_id: "3",
      role: "user",
      content: "What are the best places to visit in Paris?",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "6",
      chat_id: "3",
      role: "assistant",
      content: "Paris has so many wonderful places to visit! Here are my top recommendations:\n\n**Must-See Landmarks:**\n- Eiffel Tower - Book tickets in advance to avoid long queues\n- Louvre Museum - Home to the Mona Lisa and countless masterpieces\n- Notre-Dame Cathedral - Currently under renovation but still impressive from outside\n\n**Charming Neighborhoods:**\n- Montmartre - Artists' quarter with Sacré-Cœur basilica\n- Le Marais - Trendy area with great shops and cafés\n- Latin Quarter - Historic student area with bookshops and bistros\n\n**Hidden Gems:**\n- Sainte-Chapelle - Stunning stained glass windows\n- Canal Saint-Martin - Perfect for a leisurely stroll\n- Musée Rodin - Beautiful sculptures and gardens\n\nHow many days will you be staying?",
      created_at: new Date(Date.now() - 3600000 + 3000).toISOString(),
    },
  ],
  "4": [
    {
      id: "7",
      chat_id: "4",
      role: "user",
      content: "What are some React best practices I should follow?",
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: "8",
      chat_id: "4",
      role: "assistant",
      content: "Here are essential React best practices:\n\n**Component Structure:**\n- Keep components small and focused on a single responsibility\n- Use functional components with hooks instead of class components\n- Extract reusable logic into custom hooks\n\n**State Management:**\n- Use `useState` for local state\n- Consider Context API for global state\n- Only lift state when necessary\n\n**Performance:**\n- Use `React.memo()` for expensive components\n- Implement `useMemo` and `useCallback` to prevent unnecessary re-renders\n- Use lazy loading with `React.lazy()` and `Suspense`\n\n**Code Quality:**\n- Follow consistent naming conventions\n- PropTypes or TypeScript for type checking\n- Keep JSX clean and readable\n- Avoid inline functions in render\n\n**File Organization:**\n```\ncomponents/\n  Button/\n    Button.tsx\n    Button.test.tsx\n    Button.styles.ts\n    index.ts\n```\n\nWould you like me to elaborate on any of these points?",
      created_at: new Date(Date.now() - 1800000 + 4000).toISOString(),
    },
  ],
  "5": [
    {
      id: "9",
      chat_id: "5",
      role: "user",
      content: "Can you give me a recipe for chocolate cake?",
      created_at: new Date(Date.now() - 900000).toISOString(),
    },
    {
      id: "10",
      chat_id: "5",
      role: "assistant",
      content: "Here's a delicious chocolate cake recipe:\n\n**Ingredients:**\n- 2 cups all-purpose flour\n- 2 cups sugar\n- 3/4 cup cocoa powder\n- 2 tsp baking soda\n- 1 tsp salt\n- 2 eggs\n- 1 cup vegetable oil\n- 1 cup hot coffee\n- 1 cup buttermilk\n- 1 tsp vanilla extract\n\n**Instructions:**\n1. Preheat oven to 350°F (175°C)\n2. Grease and flour two 9-inch round pans\n3. Mix dry ingredients in a large bowl\n4. Add eggs, oil, buttermilk, and vanilla\n5. Stir in hot coffee (batter will be thin)\n6. Pour into prepared pans\n7. Bake 30-35 minutes until toothpick comes out clean\n8. Cool 10 minutes, then remove from pans\n\n**Frosting:**\n- Beat 1/2 cup butter, 2/3 cup cocoa, 3 cups powdered sugar\n- Add 1/3 cup milk and 1 tsp vanilla until smooth\n\nEnjoy your homemade chocolate cake!",
      created_at: new Date(Date.now() - 900000 + 5000).toISOString(),
    },
  ],
};

// Mock MCP servers
const mockMCPServers: MCPServer[] = [
  {
    id: "1",
    name: "Filesystem",
    description: "Access to local filesystem",
    enabled: true,
    tools: [
      { id: "1", name: "read_file", description: "Read file content", enabled: true, server_id: "1" },
      { id: "2", name: "write_file", description: "Write to file", enabled: true, server_id: "1" },
      { id: "3", name: "list_directory", description: "List directory contents", enabled: false, server_id: "1" },
    ],
  },
  {
    id: "2",
    name: "Web Search",
    description: "Search the web",
    enabled: false,
    tools: [
      { id: "4", name: "search", description: "Search web", enabled: false, server_id: "2" },
    ],
  },
];

// Mock validation items
const mockValidationItems: ValidationItem[] = [
  {
    id: "1",
    title: "Génération rapport Q4",
    description: "Le système a généré le rapport trimestriel Q4. Vérifiez les données et validez pour envoyer aux parties prenantes.",
    source: "Automatisation",
    process: "Document généré",
    agent: "GPT-4 Assistant",
    user: "Hugo Hoarau",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    status: "pending",
  },
  {
    id: "2",
    title: "Analyse sentiment client",
    description: "Analyse des retours clients du mois de novembre. 85% de satisfaction détectée avec quelques points d'amélioration identifiés.",
    source: "Agent",
    process: "Analyse",
    agent: "Code Expert",
    user: "Admin User",
    created_at: new Date(Date.now() - 7200000).toISOString(),
    status: "pending",
  },
  {
    id: "3",
    title: "Validation workflow automatisation",
    description: "Nouveau workflow d'automatisation créé pour le traitement des emails entrants. Nécessite validation avant activation.",
    source: "Chat",
    process: "Workflow",
    user: "Hugo Hoarau",
    created_at: new Date(Date.now() - 1800000).toISOString(),
    status: "pending",
  },
  {
    id: "4",
    title: "Export données analytics",
    description: "Export des données analytics pour le dashboard exécutif. Format CSV prêt à être intégré.",
    source: "Automatisation",
    process: "Export données",
    agent: "GPT-4 Assistant",
    user: "Admin User",
    created_at: new Date(Date.now() - 5400000).toISOString(),
    status: "pending",
  },
];

// Mock archived items
const mockArchivedItems: ValidationItem[] = [
  {
    id: "5",
    title: "Rapport mensuel octobre",
    description: "Rapport mensuel d'activité validé et envoyé.",
    source: "Automatisation",
    process: "Document généré",
    agent: "GPT-4 Assistant",
    user: "Hugo Hoarau",
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    status: "validated",
  },
  {
    id: "6",
    title: "Workflow onboarding",
    description: "Workflow rejeté - nécessite des ajustements sur les notifications.",
    source: "Chat",
    process: "Workflow",
    user: "Admin User",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    status: "cancelled",
  },
  {
    id: "7",
    title: "Analyse performance Q3",
    description: "Feedback demandé sur les métriques de performance.",
    source: "Agent",
    process: "Analyse",
    agent: "Code Expert",
    user: "Hugo Hoarau",
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    status: "feedback",
  },
];

// Mock API delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Auth
export async function mockLogin(email: string, password: string) {
  await delay(500);
  if (email === "admin@admin.admin" && password === "admin") {
    return { access_token: "mock_token_" + Date.now(), user_id: "1" };
  }
  throw new Error("Invalid credentials");
}

export async function mockForgotPassword(email: string) {
  await delay(500);
  return { message: "Password reset link sent" };
}

export async function mockGetUser(token: string): Promise<User> {
  await delay(200);
  return mockUser;
}

// Agents
export async function mockGetAgents(): Promise<Agent[]> {
  await delay(300);
  return [...mockAgents];
}

export async function mockCreateAgent(data: Partial<Agent>, token: string): Promise<Agent> {
  await delay(400);
  const newAgent: Agent = {
    id: String(mockAgents.length + 1),
    name: data.name || "New Agent",
    system_prompt: data.system_prompt || "",
    description: data.description,
    tags: data.tags,
    created_at: new Date().toISOString(),
    documents_count: 0,
  };
  mockAgents.push(newAgent);
  return newAgent;
}

export async function mockUpdateAgent(id: string, data: Partial<Agent>, token: string): Promise<Agent> {
  await delay(400);
  const index = mockAgents.findIndex(a => a.id === id);
  if (index === -1) throw new Error("Agent not found");
  mockAgents[index] = { ...mockAgents[index], ...data };
  return mockAgents[index];
}

export async function mockDeleteAgent(id: string, token: string) {
  await delay(300);
  const index = mockAgents.findIndex(a => a.id === id);
  if (index !== -1) mockAgents.splice(index, 1);
}

export async function mockDuplicateAgent(id: string, token: string): Promise<Agent> {
  await delay(400);
  const agent = mockAgents.find(a => a.id === id);
  if (!agent) throw new Error("Agent not found");
  const duplicate: Agent = {
    ...agent,
    id: String(mockAgents.length + 1),
    name: agent.name + " (Copy)",
    created_at: new Date().toISOString(),
  };
  mockAgents.push(duplicate);
  return duplicate;
}


// MCP
export async function mockGetMCPServers(token: string): Promise<MCPServer[]> {
  await delay(300);
  return [...mockMCPServers];
}

export async function mockToggleMCPServer(serverId: string, enabled: boolean, token: string): Promise<MCPServer> {
  await delay(300);
  const server = mockMCPServers.find(s => s.id === serverId);
  if (!server) throw new Error("Server not found");
  server.enabled = enabled;
  server.tools.forEach(tool => tool.enabled = enabled);
  return server;
}

export async function mockToggleMCPTool(toolId: string, enabled: boolean, token: string): Promise<MCPTool> {
  await delay(300);
  for (const server of mockMCPServers) {
    const tool = server.tools.find(t => t.id === toolId);
    if (tool) {
      tool.enabled = enabled;
      return tool;
    }
  }
  throw new Error("Tool not found");
}

// Validation
export async function mockGetValidationItems(token: string): Promise<ValidationItem[]> {
  await delay(300);
  return mockValidationItems.filter(item => item.status === 'pending');
}

export async function mockGetArchivedItems(token: string): Promise<ValidationItem[]> {
  await delay(300);
  return [...mockArchivedItems];
}

export async function mockValidateItem(id: string, token: string): Promise<ValidationItem> {
  await delay(400);
  const itemIndex = mockValidationItems.findIndex(item => item.id === id);
  if (itemIndex === -1) throw new Error("Item not found");

  const item = { ...mockValidationItems[itemIndex], status: 'validated' as const };
  mockValidationItems.splice(itemIndex, 1);
  mockArchivedItems.unshift(item);

  return item;
}

export async function mockCancelItem(id: string, token: string): Promise<ValidationItem> {
  await delay(400);
  const itemIndex = mockValidationItems.findIndex(item => item.id === id);
  if (itemIndex === -1) throw new Error("Item not found");

  const item = { ...mockValidationItems[itemIndex], status: 'cancelled' as const };
  mockValidationItems.splice(itemIndex, 1);
  mockArchivedItems.unshift(item);

  return item;
}

export async function mockRequestFeedback(id: string, token: string): Promise<ValidationItem> {
  await delay(400);
  const itemIndex = mockValidationItems.findIndex(item => item.id === id);
  if (itemIndex === -1) throw new Error("Item not found");

  const item = { ...mockValidationItems[itemIndex], status: 'feedback' as const };
  mockValidationItems.splice(itemIndex, 1);
  mockArchivedItems.unshift(item);

  return item;
}

// Teams
export async function mockGetTeams(token: string): Promise<Team[]> {
  await delay(300);
  return [...mockTeams];
}

export async function mockCreateTeam(data: Partial<Team>, token: string): Promise<Team> {
  await delay(400);
  const newTeam: Team = {
    id: String(mockTeams.length + 1),
    name: data.name || "New Team",
    description: data.description,
    tags: data.tags,
    system_prompt: data.system_prompt || "",
    agents: data.agents || [],
    created_at: new Date().toISOString(),
  };
  mockTeams.push(newTeam);
  return newTeam;
}

export async function mockUpdateTeam(id: string, data: Partial<Team>, token: string): Promise<Team> {
  await delay(400);
  const index = mockTeams.findIndex(t => t.id === id);
  if (index === -1) throw new Error("Team not found");
  mockTeams[index] = { ...mockTeams[index], ...data };
  return mockTeams[index];
}

export async function mockDeleteTeam(id: string, token: string) {
  await delay(300);
  const index = mockTeams.findIndex(t => t.id === id);
  if (index !== -1) mockTeams.splice(index, 1);
}

export async function mockDuplicateTeam(id: string, token: string): Promise<Team> {
  await delay(400);
  const team = mockTeams.find(t => t.id === id);
  if (!team) throw new Error("Team not found");
  const duplicate: Team = {
    ...team,
    id: String(mockTeams.length + 1),
    name: team.name + " (Copy)",
    created_at: new Date().toISOString(),
  };
  mockTeams.push(duplicate);
  return duplicate;
}

export async function mockToggleAgent(agentId: string, enabled: boolean, token: string): Promise<Agent> {
  await delay(300);
  const agent = mockAgents.find(a => a.id === agentId);
  if (!agent) throw new Error("Agent not found");
  agent.enabled = enabled;
  return agent;
}

export async function mockToggleTeam(teamId: string, enabled: boolean, token: string): Promise<Team> {
  await delay(300);
  const team = mockTeams.find(t => t.id === teamId);
  if (!team) throw new Error("Team not found");
  team.enabled = enabled;
  return team;
}

// Resource Sources
const mockResourceSources: import("./api").ResourceSource[] = [];

export async function mockGetResourceSources(token: string): Promise<import("./api").ResourceSource[]> {
  await delay(300);
  return [...mockResourceSources];
}

export async function mockCreateResourceSource(data: Partial<import("./api").ResourceSource>, token: string): Promise<import("./api").ResourceSource> {
  await delay(400);
  const newResource: import("./api").ResourceSource = {
    id: String(mockResourceSources.length + 1),
    name: data.name || "New Resource",
    description: data.description,
    type: data.type || "custom",
    enabled: data.enabled !== undefined ? data.enabled : true,
    config: data.config || {},
    methods: data.methods || [],
    created_at: new Date().toISOString(),
  };
  mockResourceSources.push(newResource);
  return newResource;
}

export async function mockUpdateResourceSource(id: string, data: Partial<import("./api").ResourceSource>, token: string): Promise<import("./api").ResourceSource> {
  await delay(400);
  const index = mockResourceSources.findIndex(r => r.id === id);
  if (index === -1) throw new Error("Resource not found");
  mockResourceSources[index] = { ...mockResourceSources[index], ...data };
  return mockResourceSources[index];
}

export async function mockDeleteResourceSource(id: string, token: string) {
  await delay(300);
  const index = mockResourceSources.findIndex(r => r.id === id);
  if (index !== -1) mockResourceSources.splice(index, 1);
}

export async function mockDuplicateResourceSource(id: string, token: string): Promise<import("./api").ResourceSource> {
  await delay(400);
  const resource = mockResourceSources.find(r => r.id === id);
  if (!resource) throw new Error("Resource not found");
  const duplicate: import("./api").ResourceSource = {
    ...resource,
    id: String(mockResourceSources.length + 1),
    name: resource.name + " (Copy)",
    created_at: new Date().toISOString(),
  };
  mockResourceSources.push(duplicate);
  return duplicate;
}

export async function mockToggleResourceSource(id: string, enabled: boolean, token: string): Promise<import("./api").ResourceSource> {
  await delay(300);
  const resource = mockResourceSources.find(r => r.id === id);
  if (!resource) throw new Error("Resource not found");
  resource.enabled = enabled;
  return resource;
}
