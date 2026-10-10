import { PanelLeftClose, PanelLeftOpen, ChevronDown, ChevronRight, Cpu, Menu, Moon, Settings2, Sun, Zap } from 'lucide-react';
import { navigation } from '../../data/navigation.js';
import { Button } from '../ui/button.jsx';

export function Sidebar({ screen, onNavigate, onSettings, close, collapsed = false, onCollapse }) {
  return <aside className={`sidebar ${close ? 'drawer-sidebar' : ''}`}>
    <a href="#twin" className="brand" onClick={event => { event.preventDefault(); onNavigate('twin'); close?.(); }} aria-label="PowerNXT digital twin"><span className="brand-icon"><Zap size={22} fill="currentColor" strokeWidth={1.5} /></span><span>Power<span className="brand-nxt">NXT</span><small>TRANSFORMER SENTINEL</small></span></a>
    <div className="workspace"><span className="workspace-icon"><Cpu size={17} /></span><div>Operations workspace<small>Single transformer</small></div><ChevronDown size={13} /></div>
    <span className="nav-caption">MONITORING</span><nav aria-label="Main navigation">{navigation.map(({ id, label, icon: Icon }) => <button key={id} className={screen === id ? 'nav-active' : ''} title={collapsed ? label : undefined} aria-label={label} aria-current={screen === id ? 'page' : undefined} onClick={() => { onNavigate(id); close?.(); }}><Icon size={17} strokeWidth={1.7} /><span>{label}</span>{screen === id && <span className="nav-indicator" />}</button>)}</nav>
    <div className="sidebar-bottom">{!close && <button className="utility-link rail-toggle" onClick={onCollapse} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}>{collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}<span>{collapsed ? 'Expand' : 'Collapse'}</span></button>}
      <button className="utility-link" onClick={() => { onSettings(); close?.(); }}><Settings2 size={16} />Connection settings</button>
      <div className="workspace-user"><span>PN</span><div>Operator workspace</div></div>
    </div>
  </aside>;
}
export function Topbar({ screen, mode, theme, onTheme, onMenu, onMode, onSettings, focused = false }) {
  return <header className="topbar"><div className="breadcrumbs"><Button className="menu-toggle" variant="ghost" size="icon" aria-label="Open navigation" onClick={onMenu}><Menu size={19} /></Button><span>Workspace</span><ChevronRight size={13} /><strong>{navigation.find(item => item.id === screen)?.label}</strong></div>
    <div className="topbar-actions"><label className="mode-picker"><span className="sr-only">Data mode</span><select aria-label="Data mode" disabled={focused} value={mode} onChange={event => onMode(event.target.value)}><option value="sample">Workspace</option><option value="live">Connected workspace</option></select></label><span className="topbar-divider" /><Button variant="ghost" size="icon" onClick={onTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</Button><Button variant="ghost" size="icon" onClick={onSettings} aria-label="Connection settings"><Settings2 size={17} /></Button></div>
  </header>;
}
