// web/src/components/settings-model.ts
// Workbench preference shape, factory defaults and the settings navigation sections.
// Author: Pierre Grothe
// Date: 2026-11-07

export interface WorkbenchPreferences {
  anthropic_api_key_masked: string;
  has_anthropic_api_key: boolean;
  anthropic_api_key_from_env: boolean;
  claude_model: string;
  auto_route_intent: boolean;
  auto_execute_intent: boolean;
  capture_viewport_width: number;
  capture_viewport_height: number;
  capture_default_media_type: 'screenshot' | 'video';
  capture_wait_timeout_ms: number;
  capture_fake_mode: boolean;
  sc_author_name: string;
  sc_author_email: string;
  default_scoped_prefix: string;
  default_brand_color: string;
  narrative_tone: string;
  sdk_fake_mode: boolean;
  show_welcome_on_startup: boolean;
  sidebar_collapsed_default: boolean;
  hud_font_scale: string;
  updated_at?: string;
}

export const DEFAULT_PREFS: WorkbenchPreferences = {
  anthropic_api_key_masked: '',
  has_anthropic_api_key: false,
  anthropic_api_key_from_env: false,
  claude_model: 'claude-sonnet-5-5',
  auto_route_intent: true,
  auto_execute_intent: true,
  capture_viewport_width: 1440,
  capture_viewport_height: 900,
  capture_default_media_type: 'screenshot',
  capture_wait_timeout_ms: 1500,
  capture_fake_mode: false,
  sc_author_name: 'Now Workbench Solution Consultant',
  sc_author_email: 'sc@servicenow.com',
  default_scoped_prefix: 'x_snc',
  default_brand_color: '#62d84e',
  narrative_tone: 'executive',
  sdk_fake_mode: false,
  show_welcome_on_startup: true,
  sidebar_collapsed_default: false,
  hud_font_scale: 'standard',
};

export type SettingsSection =
  | 'profile'
  | 'team'
  | 'groups'
  | 'approvals'
  | 'impersonate'
  | 'claude'
  | 'limits'
  | 'capture'
  | 'synthesis'
  | 'workspace'
  | 'instances';

export const SECTIONS: { id: SettingsSection; label: string; adminOnly?: boolean }[] = [
  { id: 'profile', label: 'Profile' },
  { id: 'team', label: 'Team', adminOnly: true },
  { id: 'groups', label: 'Groups' },
  { id: 'approvals', label: 'Approvals' },
  { id: 'impersonate', label: 'View as someone' },
  { id: 'claude', label: 'Claude and Otto', adminOnly: true },
  { id: 'limits', label: 'Conversation limits', adminOnly: true },
  { id: 'capture', label: 'Media capture' },
  { id: 'synthesis', label: 'Synthesis defaults' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'instances', label: 'ServiceNow instances' },
];
