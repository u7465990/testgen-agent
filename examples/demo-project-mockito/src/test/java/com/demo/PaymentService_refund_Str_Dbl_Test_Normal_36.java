package com.demo;

import com.demo.PaymentService;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_refund_Str_Dbl_Test_Normal_36 {


    @Test
    public void testRefundWithValidAmount() throws Exception {
        Constructor<?>[] ctors = PaymentService.class.getDeclaredConstructors();
        Constructor<?> ctor = ctors[0];
        Class<?>[] paramTypes = ctor.getParameterTypes();

        final int[] refundCalls = new int[1];
        final int[] notifyCalls = new int[1];

        InvocationHandler gatewayHandler = new InvocationHandler() {
            public Object invoke(Object proxy, Method method, Object[] args) {
                refundCalls[0]++;
                return null;
            }
        };
        InvocationHandler notifierHandler = new InvocationHandler() {
            public Object invoke(Object proxy, Method method, Object[] args) {
                notifyCalls[0]++;
                return null;
            }
        };

        Object gateway = Proxy.newProxyInstance(
                paramTypes[0].getClassLoader(),
                new Class<?>[] { paramTypes[0] },
                gatewayHandler);
        Object notifier = Proxy.newProxyInstance(
                paramTypes[1].getClassLoader(),
                new Class<?>[] { paramTypes[1] },
                notifierHandler);

        ctor.setAccessible(true);
        PaymentService service = (PaymentService) ctor.newInstance(gateway, notifier, "merchant-1");

        service.refund("test", 1.0);

        Assert.assertEquals(1, refundCalls[0]);
        Assert.assertEquals(1, notifyCalls[0]);
    }

}
