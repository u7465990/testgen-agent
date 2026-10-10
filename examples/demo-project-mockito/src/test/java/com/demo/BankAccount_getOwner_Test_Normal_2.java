package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_getOwner_Test_Normal_2 {


    @Test
    public void testGetOwnerReturnsOwnerName() {
        BankAccount account = new BankAccount("Alice", 1000.0);
        String result = account.getOwner();
        Assert.assertEquals("Alice", result);
    }

}
