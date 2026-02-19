import { motion } from 'framer-motion';

export function SkeletonBlock({ className = '' }) {
    return (
        <div className={`animate-pulse rounded-lg bg-primary/[0.07] ${className}`} />
    );
}

export function SkeletonText({ width = 'w-full', className = '' }) {
    return (
        <div className={`animate-pulse rounded-md bg-primary/[0.07] h-4 ${width} ${className}`} />
    );
}

export function SummarySkeleton() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8 gradient-border-left">
                <SkeletonText width="w-40" className="h-5 mb-6" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="bg-surface-input/50 rounded-xl p-4 border border-border-light">
                            <SkeletonText width="w-20" className="h-3 mb-3" />
                            <SkeletonBlock className="h-8 w-24" />
                        </div>
                    ))}
                </div>
                <div className="flex justify-center">
                    <SkeletonBlock className="h-12 w-48 rounded-full" />
                </div>
            </div>
        </motion.section>
    );
}

export function ScoreSkeleton() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                <SkeletonText width="w-44" className="h-5 mb-8" />
                <div className="flex flex-col items-center gap-8">
                    <SkeletonBlock className="w-48 h-48 sm:w-56 sm:h-56 rounded-full" />
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="rounded-xl p-4 border border-border-light text-center">
                                <SkeletonBlock className="w-8 h-8 mx-auto rounded-md mb-2" />
                                <SkeletonText width="w-20" className="h-3 mx-auto mb-2" />
                                <SkeletonBlock className="h-8 w-16 mx-auto" />
                            </div>
                        ))}
                    </div>
                </div>
                <SkeletonBlock className="mt-8 h-56 sm:h-64 w-full" />
            </div>
        </motion.section>
    );
}

export function FixesSkeleton() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                <SkeletonText width="w-40" className="h-5 mb-6" />
                <div className="flex gap-2 mb-6">
                    {[...Array(5)].map((_, i) => (
                        <SkeletonBlock key={i} className="h-8 w-20 rounded-full" />
                    ))}
                </div>
                <div className="rounded-xl border border-border-light overflow-hidden">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className={`flex items-center gap-4 px-4 py-3 ${i > 0 ? 'border-t border-border-light' : ''}`}>
                            <SkeletonText width="w-28" />
                            <SkeletonBlock className="h-5 w-16 rounded-md" />
                            <SkeletonText width="w-10" />
                            <SkeletonText width="w-48 hidden md:block" />
                            <SkeletonBlock className="h-5 w-5 rounded-full ml-auto" />
                        </div>
                    ))}
                </div>
            </div>
        </motion.section>
    );
}

export function TimelineSkeleton() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                <SkeletonText width="w-40" className="h-5 mb-8" />
                <div className="flex items-center gap-2 overflow-x-auto px-4 pb-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="flex items-center">
                            <SkeletonBlock className="min-w-[120px] sm:min-w-[140px] h-32 rounded-xl" />
                            {i < 3 && <SkeletonBlock className="h-0.5 w-8 sm:w-12 flex-shrink-0" />}
                        </div>
                    ))}
                </div>
                <SkeletonText width="w-64" className="mx-auto mt-4" />
            </div>
        </motion.section>
    );
}
