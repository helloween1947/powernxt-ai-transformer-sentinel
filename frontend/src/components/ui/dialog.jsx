import { useLayoutEffect, useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, useReducedMotion } from 'motion/react';
import { inspectionEntry, motionTiming } from '../../domain/motion.js';
import { occurredBeforeOpen } from '../../domain/dialogInteraction.js';
import { X } from 'lucide-react';
import { Button } from './button.jsx';

// shadcn/ui Dialog composition using Radix's keyboard and focus management.
export function DetailDialog({ open, onOpenChange, title, description, children, sheet = false }) {
  const reduced = useReducedMotion();
  const sourceFocus = useRef(null);
  const contentRef = useRef(null);
  const closeRef = useRef(null);
  const openedAt = useRef(null);
  useLayoutEffect(() => {
    // A reopened dialog can still be mounted during its previous close fade.
    if (open && contentRef.current) {
      openedAt.current = performance.now();
      if (!contentRef.current.contains(document.activeElement)) sourceFocus.current = document.activeElement;
      closeRef.current?.focus({ preventScroll: true });
    }
  }, [open]);
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal>
    <Dialog.Overlay className="dialog-overlay" />
    <Dialog.Content ref={contentRef} {...(!description ? { 'aria-describedby': undefined } : {})} onInteractOutside={event => { if (!open || occurredBeforeOpen(event.detail.originalEvent?.timeStamp, openedAt.current)) event.preventDefault(); }} onOpenAutoFocus={event => { event.preventDefault(); if (!contentRef.current?.contains(document.activeElement)) sourceFocus.current = document.activeElement; closeRef.current?.focus({ preventScroll: true }); }} onCloseAutoFocus={event => { if (sourceFocus.current?.isConnected && sourceFocus.current !== document.body) { event.preventDefault(); sourceFocus.current.focus({ preventScroll: true }); } }} className={`dialog-position ${sheet ? 'sheet-position' : ''}`}><motion.section className={`dialog-content ${sheet ? 'mobile-sheet' : ''}`} initial={inspectionEntry(reduced)} animate={{ opacity: 1, y: 0 }} transition={reduced ? { duration: 0 } : motionTiming.view}>
      <div className="inspection-content">
      <div className="dialog-heading"><div><Dialog.Title>{title}</Dialog.Title>{description && <Dialog.Description>{description}</Dialog.Description>}</div>
        <Dialog.Close asChild><Button ref={closeRef} variant="ghost" size="icon" aria-label="Close dialog"><X size={18} /></Button></Dialog.Close>
      </div>{children}</div>
    </motion.section></Dialog.Content>
  </Dialog.Portal></Dialog.Root>;
}
