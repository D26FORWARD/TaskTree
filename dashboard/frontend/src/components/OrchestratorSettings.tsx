import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { api } from '@/services/api';
import { OrchestratorConfig } from '@/types';
import { Key, Brain, Save, AlertCircle, CheckCircle, Server, Hash } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const PROVIDER_OPTIONS = [
  { id: 'anthropic', name: 'Anthropic', defaultBaseUrl: 'https://api.anthropic.com/v1' },
  { id: 'openai', name: 'OpenAI', defaultBaseUrl: 'https://api.openai.com/v1' },
  { id: 'azure', name: 'Azure OpenAI', defaultBaseUrl: '' },
  { id: 'aliyun', name: '阿里云百炼', defaultBaseUrl: 'https://dashscope.aliyuncs.com/api/v1' },
  { id: 'custom', name: 'Custom Provider', defaultBaseUrl: '' },
];

const ANTHROPIC_MODELS = [
  { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4 (Latest)', pricing: '$3/$15' },
  { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', pricing: '$15/$75' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', pricing: '$3/$15' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', pricing: '$0.80/$4' },
  { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', pricing: '$15/$75' },
  { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', pricing: '$0.25/$1.25' },
];

const OPENAI_MODELS = [
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', pricing: '$10/$30' },
  { id: 'gpt-4', name: 'GPT-4', pricing: '$30/$60' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', pricing: '$0.50/$1.50' },
];

const ALIYUN_MODELS = [
  { id: 'qwen-plus', name: 'Qwen Plus', pricing: '按token计费' },
  { id: 'qwen-turbo', name: 'Qwen Turbo', pricing: '按token计费' },
  { id: 'qwen-max', name: 'Qwen Max', pricing: '按token计费' },
  { id: 'qwen-long', name: 'Qwen Long', pricing: '按token计费' },
  { id: 'custom', name: '自定义模型', pricing: '按token计费' },
];

export function OrchestratorSettings() {
  const [apiKey, setApiKey] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('anthropic');
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4-20250514');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiVersion, setApiVersion] = useState('');
  const [aliyunAppId, setAliyunAppId] = useState('');  // For Aliyun app ID
  const [showApiKey, setShowApiKey] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const queryClient = useQueryClient();

  // Fetch current config
  const { data: config } = useQuery({
    queryKey: ['orchestrator-config'],
    queryFn: api.getOrchestratorConfig,
  });

  // Update state when config loads
  useEffect(() => {
    if (config) {
      setApiKey(config.api_key || '');
      setSelectedProvider(config.api_provider || 'anthropic');
      // For Aliyun provider, load app ID from api_version and model from api_model
      if (config.api_provider === 'aliyun') {
        setSelectedModel(config.api_model || 'qwen-plus');
        setAliyunAppId(config.api_version || '');
      } else {
        setSelectedModel(config.api_model || 'claude-sonnet-4-20250514');
      }
      setApiBaseUrl(config.api_base_url || '');
      setApiVersion(config.api_provider === 'aliyun' ? '' : (config.api_version || ''));
    }
  }, [config]);

  // Update base URL when provider changes
  useEffect(() => {
    const provider = PROVIDER_OPTIONS.find(p => p.id === selectedProvider);
    if (provider && !apiBaseUrl) {
      setApiBaseUrl(provider.defaultBaseUrl);
    }
  }, [selectedProvider, apiBaseUrl]);

  const updateConfigMutation = useMutation({
    mutationFn: (updates: Partial<OrchestratorConfig>) =>
      api.updateOrchestratorConfig({ ...config!, ...updates }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orchestrator-config'] });
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 3000);
    },
    onError: () => {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  });

  const handleSave = () => {
    setSaveStatus('saving');
    // For Aliyun provider, save app ID in api_version
    let versionToSave = apiVersion;
    if (selectedProvider === 'aliyun' && aliyunAppId) {
      versionToSave = aliyunAppId;  // Store app ID in api_version
    }

    updateConfigMutation.mutate({
      api_key: apiKey,
      api_provider: selectedProvider,
      api_model: selectedModel,
      api_base_url: apiBaseUrl,
      api_version: versionToSave
    });
  };

  const getModelOptions = () => {
    switch (selectedProvider) {
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

  const selectedModelInfo = getModelOptions().find(m => m.id === selectedModel);

  return (
    <Card className="bg-deep-indigo/50 border-electric-cyan/20">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Key className="w-5 h-5" />
          <span>API Configuration</span>
        </CardTitle>
        <CardDescription>
          Configure your API key and model preferences for plan generation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="provider">API Provider</Label>
          <Select value={selectedProvider} onValueChange={setSelectedProvider}>
            <SelectTrigger className="bg-dark-bg/50 border-electric-cyan/20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROVIDER_OPTIONS.map(provider => (
                <SelectItem key={provider.id} value={provider.id}>
                  {provider.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Select your AI provider. For custom/self-hosted providers, choose "Custom Provider".
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="api-key">API Key</Label>
          <div className="flex space-x-2">
            <Input
              id="api-key"
              type={showApiKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={selectedProvider === 'anthropic' ? "sk-ant-..." : "Enter your API key"}
              className="bg-dark-bg/50 border-electric-cyan/20"
              autoComplete="off"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowApiKey(!showApiKey)}
              className="border-electric-cyan/20"
            >
              {showApiKey ? 'Hide' : 'Show'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Your API key is stored locally and used only for plan generation.
            {selectedProvider === 'anthropic' && (
              <span> Get one at <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="text-electric-cyan hover:underline">console.anthropic.com</a></span>
            )}
            {selectedProvider === 'openai' && (
              <span> Get one at <a href="https://platform.openai.com" target="_blank" rel="noopener noreferrer" className="text-electric-cyan hover:underline">platform.openai.com</a></span>
            )}
            {selectedProvider === 'aliyun' && (
              <span> 从<a href="https://bailian.console.aliyun.com/?tab=model#/api-key" target="_blank" rel="noopener noreferrer" className="text-electric-cyan hover:underline">阿里云百炼控制台</a>获取 API 密钥</span>
            )}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="base-url">API Base URL</Label>
          <div className="flex space-x-2">
            <Input
              id="base-url"
              type="text"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder="https://api.provider.com/v1"
              className="bg-dark-bg/50 border-electric-cyan/20"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                const provider = PROVIDER_OPTIONS.find(p => p.id === selectedProvider);
                if (provider) {
                  setApiBaseUrl(provider.defaultBaseUrl);
                }
              }}
              className="border-electric-cyan/20"
            >
              <Server className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Base URL for the API endpoint. For most providers, the default is sufficient.
            For Azure OpenAI, you'll need to provide your specific endpoint URL.
          </p>
        </div>

        {selectedProvider === 'azure' && (
          <div className="space-y-2">
            <Label htmlFor="api-version">API Version</Label>
            <div className="flex space-x-2">
              <Input
                id="api-version"
                type="text"
                value={apiVersion}
                onChange={(e) => setApiVersion(e.target.value)}
                placeholder="2024-05-01-preview"
                className="bg-dark-bg/50 border-electric-cyan/20"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setApiVersion('2024-05-01-preview')}
                className="border-electric-cyan/20"
              >
                <Hash className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              API version for Azure OpenAI. Usually in the format YYYY-MM-DD.
            </p>
          </div>
        )}

        {selectedProvider === 'aliyun' && (
          <div className="space-y-2">
            <Label htmlFor="aliyun-app-id">阿里云百炼应用 ID</Label>
            <Input
              id="aliyun-app-id"
              type="text"
              value={aliyunAppId}
              onChange={(e) => setAliyunAppId(e.target.value)}
              placeholder="请输入您的应用 ID (APP_ID)"
              className="bg-dark-bg/50 border-electric-cyan/20"
            />
            <p className="text-xs text-muted-foreground">
              从<a href="https://bailian.console.aliyun.com/?tab=app#/app-center" target="_blank" rel="noopener noreferrer" className="text-electric-cyan hover:underline">阿里云百炼控制台</a>获取应用 ID
            </p>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="model">Model</Label>
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="bg-dark-bg/50 border-electric-cyan/20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {getModelOptions().map(model => (
                <SelectItem key={model.id} value={model.id}>
                  <div className="flex items-center justify-between w-full">
                    <span>{model.name}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      {selectedProvider === 'aliyun' ? model.pricing : model.pricing + ' per MTok'}
                    </span>
                  </div>
                </SelectItem>
              ))}

            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Select the model to use for plan generation. Pricing varies by provider and model.
          </p>
        </div>

        {selectedModelInfo && (
          <Alert className="border-electric-cyan/20">
            <Brain className="h-4 w-4" />
            <AlertDescription>
              <strong>{selectedModelInfo.name}</strong> costs {selectedModelInfo.pricing} per million tokens (input/output).
              Plan generation typically uses ~2-3k input and ~2-4k output tokens.
              Estimated cost per plan: ~$0.02-0.08
            </AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-between pt-4">
          <div className="flex items-center space-x-2">
            {saveStatus === 'saved' && (
              <div className="flex items-center space-x-1 text-green-500">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm">Settings saved</span>
              </div>
            )}
            {saveStatus === 'error' && (
              <div className="flex items-center space-x-1 text-red-500">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">Failed to save</span>
              </div>
            )}
          </div>
          <Button
            onClick={handleSave}
            disabled={updateConfigMutation.isPending || !apiKey}
            variant="glow"
          >
            <Save className="w-4 h-4 mr-2" />
            {updateConfigMutation.isPending ? 'Saving...' : 'Save API Settings'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
