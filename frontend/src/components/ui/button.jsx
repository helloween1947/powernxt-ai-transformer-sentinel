import { Slot } from '@radix-ui/react-slot';
import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils.js';

// shadcn/ui button pattern (MIT), styled with the workstation's semantic tokens.
const variants = cva('ui-button', {
  variants: {
    variant: { default: 'button-primary', outline: 'button-outline', ghost: 'button-ghost', secondary: 'button-secondary' },
    size: { default: '', sm: 'button-sm', icon: 'button-icon' },
  }, defaultVariants: { variant: 'default', size: 'default' },
});
export function Button({ className, variant, size, asChild = false, ...props }) {
  const Component = asChild ? Slot : 'button';
  return <Component type={asChild ? undefined : 'button'} className={cn(variants({ variant, size }), className)} {...props} />;
}
