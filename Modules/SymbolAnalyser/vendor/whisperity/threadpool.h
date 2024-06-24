#ifndef WHISPERITY_THREADPOOL_H
#define WHISPERITY_THREADPOOL_H

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

namespace whisperity
{
/**
 * @brief A simple thread pool iterating a list of jobs. This is a base class
 * to support overloading based on whether or not we want actual multithreading.
 *
 * @tparam JobData    Jobs are represented in a custom, user-defined structure.
 */
template <typename JobData>
class JobQueueThreadPool
{
    // This class implements the 'Curiously Recurring Template Pattern'
    // to provide an optimised overload for actually single-threaded execution.
public:
    virtual ~JobQueueThreadPool()
    {}

    /**
     * @brief Enqueue a new job to be executed by the thread pool.
     *
     * @warning Job execution might start immediately at enqueue's return!
     *
     * @param JobInfo  The job object to work on.
     */
    virtual void enqueue(JobData JobInfo) = 0;

    /**
     * @brief Notify all workers to exit after doing the remaining work
     * and wait for the threads to die.
     */
    virtual void wait() = 0;
};

/**
 * @brief Single-thread optimised, synchronous version of JobQueueThreadPool.
 *
 * This class does not create any workers, but rather executes every incoming
 * job synchronously before giving back control to the client code.
 *
 * @tparam JobData   Jobs are represented in a custom, user-defined structure.
 * @tparam Function  A user defined functor which the workers call to do the
 * actual work. This functor must accept a JobData as its argument.
 */
template <typename JobData,
          typename Function = std::function<void (JobData)>>
class SingleThreadJobQueue : public JobQueueThreadPool<JobData>
{
public:
    /**
     * Create a single-thread optimised "pool" object which executes jobs in
     * a synchronous way.
     *
     * @param Fun         The function to execute on the jobs.
     */
    SingleThreadJobQueue(Function Fun) : Fun(Fun)
    {}

    /**
     * @brief Execute the thread pool's function on the given job.
     *
     * The single-threaded "pool" synchronously runs the job immediately.
     *
     * @param JobInfo  The job object to work on.
     */
    void enqueue(JobData JobInfo)
    {
        Fun(JobInfo);
    }

    /**
     * @brief Has no effect in single-threaded operation as enqueue()
     * automatically runs the job function.
     */
    void wait()
    {}

private:
    /**
     * The function which is executed on incoming jobs.
     */
    Function Fun;
};

/**
 * @brief A simple thread pool which iterates a set of jobs dynamically.
 *
 * This class creates N worker threads in the background which are waken up
 * as jobs are added to the queue. Each worker takes a single job and executes
 * it, and the threads return to sleep.
 *
 * @tparam JobData   Jobs are represented in a custom, user-defined structure.
 * @tparam Function  A user defined functor which the workers call to do the
 * actual work. This functor must accept a JobData as its argument.
 */
template <typename JobData,
          typename Function = std::function<void (JobData)>>
class PooledJobQueue : public JobQueueThreadPool<JobData>
{
public:
    /**
     * Create a new thread pool with the given number of threads and using the
     * given function as its work logic.
     *
     * @param ThreadCount  The number of worker threads to create.
     * @param Fun          The function to execute on the enqueued jobs.
     */
    PooledJobQueue(size_t ThreadCount, Function Fun)
        : ThreadCount(ThreadCount), Die(false)
    {
        for (size_t I = 0; I < ThreadCount; ++I)
            Threads.emplace_back(std::thread(
                &PooledJobQueue<JobData, Function>::worker,
                this, Fun));
    }

    ~PooledJobQueue()
    {
        if (!Die)
            wait();
    }

    /**
     * @brief Enqueue a new job to be executed by the thread pool.
     *
     * @warning Job execution might start immediately at enqueue's return!
     *
     * @param JobInfo  The job object to work on.
     */
    void enqueue(JobData JobInfo)
    {
        {
            std::lock_guard<std::mutex> Lock(this->Lock);
            Queue.push(JobInfo);
        }

        Signal.notify_one();
    }

    /**
     * @brief Notify all workers to exit after doing the remaining work
     * and wait for the threads to die.
     */
    void wait()
    {
        Die = true;
        Signal.notify_all();

        for (std::thread& t : Threads)
        {
            // Keep nudging the threads so that the t.join() don't grind the
            // system to a halt.
            Signal.notify_all();
            if (t.joinable())
                t.join();
        }
    }

private:
    /**
     * @brief The worker method loops and waits for jobs to come and executes
     * function on them.
     */
    void worker(Function Fun)
    {
        while (!(Die && Queue.empty()))
            // The race condition here is known and allowed deliberately.
        {
            // Lock on the mutex so that the queue access is safe.
            std::unique_lock<std::mutex> Lock(this->Lock);
            if (Queue.empty())
            {
                // If the queue is empty, we have to wait for new work to be
                // enqueued. The thread is randomly woken up from time to time
                // to ensure that work is being done, even if an enqueue() call
                // could not notify any thread, because noone was waiting.
                Signal.wait_for(Lock, std::chrono::seconds(1), [this]()
                {
                    return !Queue.empty();
                });

                // Signal hit: work has been given to us, Lock is reacquired.
                // Release the Lock and notify other thread that we will be
                // working.
                Lock.unlock();
                Signal.notify_one();

                // Next cycle will take the work if noone snatches it from us.
                continue;
            }
            else
            {
                // The queue was not empty, we can do actual work.
                JobData Job = Queue.front();
                Queue.pop();

                // After popping, we are out of the critical section.
                // Give the Lock back and signal another thread.
                Lock.unlock();
                Signal.notify_one();

                // Do work.
                Fun(Job);
            }
        }
    }

    /**
     * The number of worker threads created when the class is instantiated.
     */
    const size_t ThreadCount;

    /**
     * std::mutex for accessing the _queue.
     */
    std::mutex Lock;

    /**
     * Condition variable to wake up worker threads.
     */
    std::condition_variable Signal;

    /**
     * _die controls whether or not executing workers must stop forever
     * waiting for new job to be queued and should stop after doing work.
     */
    std::atomic_bool Die;

    /**
     * The queue contains the JobData objects which define the jobs the pool
     * executes.
     */
    std::queue<JobData> Queue;

    /**
     * Contains the worker threads.
     */
    std::vector<std::thread> Threads;
};

/**
 * @brief Create an std::unique_ptr for a thread pool with the given number of
 * threads.
 *
 * @tparam JobData   Jobs are represented in a custom, user-defined structure.
 * @tparam Function  A user defined functor which the workers call to do the
 * actual work. This functor must accept a JobData as its argument.
 * @param ThreadCount  The number of threads the threadpool should use.
 * @param Fun          The function to execute on the enqueued jobs.
 * @param ForceAsync   If threadCount is 1, ThreadPool can use a synchronous,
 * single-thread optimised version. However, there can be the case that the
 * client code specifically wants an async pool, which can be requested by
 * setting this variable to True. This variable has no effect if threadCount is
 * more than 1.
 * @return An std::unique_ptr containing a thread pool.
 */
template <typename JobData, typename Function>
std::unique_ptr<JobQueueThreadPool<JobData>> make_thread_pool(
    const size_t ThreadCount,
    Function Fun,
    bool ForceAsync = false)
{
    if (ThreadCount == 1 && !ForceAsync)
        // Optimise for single-threaded execution!
        return std::make_unique<SingleThreadJobQueue<JobData, Function>>(Fun);
    else
        return std::make_unique<PooledJobQueue<JobData, Function>>(ThreadCount,
                                                                   Fun);
}

} // namespace whisperity

#endif // WHISPERITY_THREADPOOL_H
