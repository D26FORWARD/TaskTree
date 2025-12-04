import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Settings,
  Key,
  Brain,
  Users,
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Save,
  RefreshCw,
  Server,
  Hash
} from 'lucide-react';

interface OrchestratorConfig {
  max_concurrent_agents: number;
  auto_merge: boolean;
  merge_strategy: string;
  auto_spawn_interval: number;
  enabled: boolean;
  api_provider: string;  // API provider: "anthropic", "openai", "azure", etc.
  api_key?: string;  // Generic API key for plan generation
  api_model?: string;  // Model to use for generation
  api_base_url?: string;  // Base URL for API endpoint (for custom/self-hosted providers)
  api_version?: string;  // API version (for providers that require it)
}

const PROVIDER_OPTIONS = [
  { id: 'anthropic', name: 'Anthropic', defaultBaseUrl: 'https://api.anthropic.com/v1' },
  { id: 'openai', name: 'OpenAI', defaultBaseUrl: 'https://api.openai.com/v1' },
  { id: 'azure', name: 'Azure OpenAI', defaultBaseUrl: '' },
  { id: 'aliyun', name: '阿里云百炼', defaultBaseUrl: 'https://dashscope.aliyuncs.com/api/v1' },
  { id: 'custom', name: 'Custom Provider', defaultBaseUrl: '' },
];

const ANTHROPIC_MODELS = [
  { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', pricing: '$15/$75' },
  { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', pricing: '$3/$15' },
  { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', pricing: '$0.25/$1.25' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', pricing: '$3/$15' },
];

const OPENAI_MODELS = [
  { id: 'gpt-4', name: 'GPT-4', pricing: '$30/$60' },
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', pricing: '$10/$30' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', pricing: '$0.50/$1.50' },
];

const ALIYUN_MODELS = [
  { id: 'qwen-plus', name: 'Qwen Plus', pricing: '按token计费' },
  { id: 'qwen-turbo', name: 'Qwen Turbo', pricing: '按token计费' },
  { id: 'qwen-max', name: 'Qwen Max', pricing: '按token计费' },
  { id: 'qwen-long', name: 'Qwen Long', pricing: '按token计费' },
  { id: 'custom', name: '自定义模型', pricing: '按token计费' },
];

export function GlobalSettings() {
  const [showApiKey, setShowApiKey] = useState(false);
  const [aliyunAppId, setAliyunAppId] = useState('');  // For Aliyun app ID
  const [formData, setFormData] = useState<OrchestratorConfig>({
    max_concurrent_agents: 5,
    auto_merge: false,
    merge_strategy: 'merge',
    auto_spawn_interval: 60,
    enabled: false,
    api_provider: 'anthropic',
    api_key: '',
    api_model: 'claude-3-sonnet-20240229',
    api_base_url: '',
    api_version: '',
  });
  const [hasChanges, setHasChanges] = useState(false);

  const queryClient = useQueryClient();

  // Fetch current configuration
  const { data: config, isLoading, error } = useQuery({
    queryKey: ['orchestrator-config'],
    queryFn: async () => {
      const response = await fetch('/api/orchestrator/config');
      if (!response.ok) throw new Error('Failed to fetch configuration');
      return response.json();
    },
  });

  // Update configuration mutation
  const updateMutation = useMutation({
    mutationFn: async (newConfig: OrchestratorConfig) => {
      const response = await fetch('/api/orchestrator/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig),
      });
      if (!response.ok) throw new Error('Failed to update configuration');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orchestrator-config'] });
      setHasChanges(false);
    },
  });

  // Load config data into form when it arrives
  useEffect(() => {
    if (config) {
      setFormData(config);
      // For Aliyun, extract app ID from api_base_url or from a separate field if it exists
      if (config.api_provider === 'aliyun' && config.api_base_url?.includes('app')) {
        // Extract app ID from URL if needed
        const appIdMatch = config.api_base_url.match(/\/apps\/([^/]+)/);
        if (appIdMatch) setAliyunAppId(appIdMatch[1]);
      }
    }
  }, [config]);

  // Track changes
  useEffect(() => {
    if (config) {
      const changed = JSON.stringify(config) !== JSON.stringify(formData);
      setHasChanges(changed);
    }
  }, [config, formData]);

  // Update base URL when provider changes
  useEffect(() => {
    const provider = PROVIDER_OPTIONS.find(p => p.id === formData.api_provider);
    if (provider && !formData.api_base_url) {
      setFormData(prev => ({
        ...prev,
        api_base_url: provider.defaultBaseUrl
      }));
    }
  }, [formData.api_provider, formData.api_base_url]);

  const handleInputChange = (field: keyof OrchestratorConfig, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = () => {
    // For Aliyun, save app ID in api_base_url
    let saveData = { ...formData };
    if (formData.api_provider === 'aliyun' && aliyunAppId) {
      // Store app ID in api_version for now (can be extended to a separate field later)
      saveData.api_version = aliyunAppId;
    }
    updateMutation.mutate(saveData);
  };

  const handleReset = () => {
    if (config) {
      setFormData(config);
    }
  };

  const validateApiKey = (key: string, provider: string) => {
    if (!key) return false;

    switch (provider) {
      case 'anthropic':
        return key.startsWith('sk-ant-') && key.length > 20;
      case 'openai':
        return key.startsWith('sk-') && key.length > 20;
      case 'azure':
        return key.length > 10; // Azure keys can have different formats
      default:
        return key.length > 5; // Generic validation
    }
  };

  const getModelOptions = () => {
    switch (formData.api_provider) {
      case 'anthropic':
        return ANTHROPIC_MODELS;
      case 'openai':
      case 'azure':
        return OPENAI_MODELS;
      case 'aliyun':
        return ALIYUN_MODELS;
      default:
        // For custom providers, return a mix of common models
        return [...ANTHROPIC_MODELS, ...OPENAI_MODELS];
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-electric-cyan mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className="border-red-500/20 bg-red-500/5">
        <AlertCircle className="h-4 w-4 text-red-500" />
        <AlertDescription>
          Failed to load configuration settings
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Settings className="w-8 h-8 text-electric-cyan" />
            Global Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure SplitMind orchestrator and API settings
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {hasChanges && (
            <Badge variant="outline" className="text-yellow-400 border-yellow-400/20">
              Unsaved Changes
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || updateMutation.isPending}
          >
            <Save className="w-4 h-4 mr-2" />
            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Configuration */}
        <Card className="border-electric-cyan/20 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-electric-cyan" />
              API Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider">API Provider</Label>
              <Select
                value={formData.api_provider}
                onValueChange={(value) => handleInputChange('api_provider', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDER_OPTIONS.map(provider => (
                    <SelectItem key={provider.id} value={provider.id}>
                      {provider.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <div className="relative">
                <Input
                  id="api-key"
                  type={showApiKey ? "text" : "password"}
                  value={formData.api_key || ''}
                  onChange={(e) => handleInputChange('api_key', e.target.value)}
                  placeholder={formData.api_provider === 'anthropic' ? "sk-ant-..." : "Enter your API key"}
                  className="pr-20"
                />
                <div className="absolute right-2 top-2.5 flex items-center space-x-1">
                  {formData.api_key && validateApiKey(formData.api_key, formData.api_provider) && (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="h-6 w-6 p-0"
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              {formData.api_key && !validateApiKey(formData.api_key, formData.api_provider) && (
                <p className="text-xs text-red-400">Invalid API key format for {PROVIDER_OPTIONS.find(p => p.id === formData.api_provider)?.name}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="base-url">API Base URL</Label>
              <div className="flex space-x-2">
                <Input
                  id="base-url"
                  type="text"
                  value={formData.api_base_url || ''}
                  onChange={(e) => handleInputChange('api_base_url', e.target.value)}
                  placeholder="https://api.provider.com/v1"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const provider = PROVIDER_OPTIONS.find(p => p.id === formData.api_provider);
                    if (provider) {
                      handleInputChange('api_base_url', provider.defaultBaseUrl);
                    }
                  }}
                >
                  <Server className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {formData.api_provider === 'azure' && (
              <div className="space-y-2">
                <Label htmlFor="api-version">API Version</Label>
                <div className="flex space-x-2">
                  <Input
                    id="api-version"
                    type="text"
                    value={formData.api_version || ''}
                    onChange={(e) => handleInputChange('api_version', e.target.value)}
                    placeholder="2024-05-01-preview"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleInputChange('api_version', '2024-05-01-preview')}
                  >
                    <Hash className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}

            {formData.api_provider === 'aliyun' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="aliyun-app-id">阿里云百炼应用 ID</Label>
                  <Input
                    id="aliyun-app-id"
                    type="text"
                    value={aliyunAppId}
                    onChange={(e) => setAliyunAppId(e.target.value)}
                    placeholder="请输入您的应用 ID (APP_ID)"
                  />
                  <p className="text-xs text-muted-foreground">
                    从<a href="https://bailian.console.aliyun.com/?tab=app#/app-center" target="_blank" rel="noopener noreferrer" className="text-electric-cyan hover:underline">阿里云百炼控制台</a>获取应用 ID
                  </p>
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              {formData.api_provider === 'aliyun' ? (
                <Select
                  value={formData.api_model || 'qwen-plus'}
                  onValueChange={(value) => handleInputChange('api_model', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择模型" />
                  </SelectTrigger>
                  <SelectContent>
                    {getModelOptions().map(model => (
                      <SelectItem key={model.id} value={model.id}>
                        <div className="flex items-center justify-between w-full">
                          <span>{model.name}</span>
                          <span className="text-xs text-muted-foreground ml-2">
                            {model.pricing}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Select
                  value={formData.api_model || 'claude-3-sonnet-20240229'}
                  onValueChange={(value) => handleInputChange('api_model', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    {getModelOptions().map(model => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <Alert className="border-blue-500/20 bg-blue-500/5">
              <Key className="h-4 w-4 text-blue-500" />
              <AlertDescription className="text-xs">
                Your API key is stored securely and used for AI plan generation and task processing.
                {formData.api_provider === 'anthropic' && (
                  <span> Get your key from the <a
                    href="https://console.anthropic.com/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-electric-cyan hover:underline"
                  >
                    Anthropic Console
                  </a></span>
                )}
                {formData.api_provider === 'openai' && (
                  <span> Get your key from the <a
                    href="https://platform.openai.com/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-electric-cyan hover:underline"
                  >
                    OpenAI Platform
                  </a></span>
                )}
                {formData.api_provider === 'aliyun' && (
                  <span> 从<a
                    href="https://bailian.console.aliyun.com/?tab=model#/api-key"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-electric-cyan hover:underline"
                  >
                    阿里云百炼控制台
                  </a>获取 API 密钥 (DashScope API Key)</span>
                )}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Orchestrator Configuration */}
        <Card className="border-electric-cyan/20 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-electric-cyan" />
              Orchestrator Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">Enable Orchestrator</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically spawn and manage AI agents
                </p>
              </div>
              <Switch
                checked={formData.enabled}
                onCheckedChange={(checked) => handleInputChange('enabled', checked)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-agents">Max Concurrent Agents</Label>
              <Input
                id="max-agents"
                type="number"
                min="1"
                max="20"
                value={formData.max_concurrent_agents}
                onChange={(e) => handleInputChange('max_concurrent_agents', parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="spawn-interval">Auto Spawn Interval (seconds)</Label>
              <Input
                id="spawn-interval"
                type="number"
                min="10"
                max="600"
                value={formData.auto_spawn_interval}
                onChange={(e) => handleInputChange('auto_spawn_interval', parseInt(e.target.value) || 60)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">Auto Merge</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically merge completed tasks
                </p>
              </div>
              <Switch
                checked={formData.auto_merge}
                onCheckedChange={(checked) => handleInputChange('auto_merge', checked)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="merge-strategy">Merge Strategy</Label>
              <Select
                value={formData.merge_strategy}
                onValueChange={(value) => handleInputChange('merge_strategy', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="merge">Merge (create merge commit)</SelectItem>
                  <SelectItem value="rebase">Rebase (linear history)</SelectItem>
                  <SelectItem value="squash">Squash (single commit)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status Information */}
      <Card className="border-electric-cyan/20 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-electric-cyan" />
            Configuration Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${formData.api_key && validateApiKey(formData.api_key, formData.api_provider)
                ? 'bg-green-500'
                : 'bg-red-500'
                }`}></div>
              <span className="text-sm">API Key {
                formData.api_key && validateApiKey(formData.api_key, formData.api_provider)
                  ? 'Valid'
                  : 'Invalid'
              }</span>
            </div>

            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${formData.enabled ? 'bg-green-500' : 'bg-gray-500'
                }`}></div>
              <span className="text-sm">Orchestrator {formData.enabled ? 'Enabled' : 'Disabled'}</span>
            </div>

            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${hasChanges ? 'bg-yellow-500' : 'bg-green-500'
                }`}></div>
              <span className="text-sm">{hasChanges ? 'Unsaved Changes' : 'Settings Saved'}</span>
            </div>
          </div>

          {hasChanges && (
            <Alert className="border-yellow-500/20 bg-yellow-500/5 mt-4">
              <AlertCircle className="h-4 w-4 text-yellow-500" />
              <AlertDescription className="text-xs">
                You have unsaved changes. Click "Save Settings" to apply them.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
